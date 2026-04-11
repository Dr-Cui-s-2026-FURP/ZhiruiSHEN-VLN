import os
import subprocess
from typing import Optional


def _patch_params4bit_constructor() -> None:
    """Compatibility patch for older bitsandbytes versions.

    Some transformer versions pass `_is_hf_initialized` into Params4bit.
    Older bitsandbytes releases don't accept that kwarg and crash during load.
    """
    try:
        from bitsandbytes.nn.modules import Params4bit
    except Exception:
        return

    original_new = Params4bit.__new__
    if getattr(original_new, "_vln_patched", False):
        return

    def _patched_new(cls, *args, **kwargs):
        kwargs.pop("_is_hf_initialized", None)
        return original_new(cls, *args, **kwargs)

    _patched_new._vln_patched = True
    Params4bit.__new__ = staticmethod(_patched_new)


def _move_inputs_for_auto_device(inputs, model):
    """Avoid forcing CUDA when model uses device_map='auto' with CPU/disk offload."""
    try:
        model_device = getattr(model, "device", None)
        if model_device is not None and str(model_device) != "meta":
            return inputs.to(model_device)
    except Exception:
        pass
    return inputs


class QwenVLWrapper:
    """Local Qwen3-VL wrapper with lazy loading for Node 5."""

    def __init__(
        self,
        model_path: str,
        max_new_tokens: int = 256,
        mode: str = "subprocess",
        conda_env: str = "isaaclab",
        inference_script_path: str = "/home/bluepoisons/Desktop/FURP/VLN/ZhiruiSHEN-VLN/src/vln_inference/run_inference_cli.py",
    ) -> None:
        self.model_path = model_path
        self.max_new_tokens = max_new_tokens
        self.mode = mode
        self.conda_env = conda_env
        self.inference_script_path = inference_script_path
        self._model = None
        self._processor = None

    def _ensure_loaded(self) -> None:
        if self.mode != "local":
            return

        if self._model is not None and self._processor is not None:
            return

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model path not found: {self.model_path}")

        # Import heavy ML dependencies only in local mode.
        from PIL import Image  # noqa: F401
        import torch
        from transformers import AutoProcessor, BitsAndBytesConfig, Qwen3VLForConditionalGeneration

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            llm_int8_enable_fp32_cpu_offload=True,
        )

        _patch_params4bit_constructor()

        self._model = Qwen3VLForConditionalGeneration.from_pretrained(
            self.model_path,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
        )
        self._processor = AutoProcessor.from_pretrained(
            self.model_path,
            trust_remote_code=True,
        )

    def infer_goal_text(self, instruction: str, image_path: str) -> str:
        """Run vision-language inference and return model text output."""
        if self.mode == "subprocess":
            return self._infer_via_subprocess(instruction=instruction, image_path=image_path)

        self._ensure_loaded()

        from PIL import Image

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image path not found: {image_path}")

        raw_image = Image.open(image_path).convert("RGB")

        prompt = (
            "You are a warehouse navigation assistant. "
            "Here is the exact map memory of the environment: "
            "[shelf with purple boxes is at x=-6.78, y=10.96], "
            "[plant is at x=-0.43, y=-2.92], "
            "[chair is at x=-0.54, y=-0.69]. "
            "Given the user instruction and scene image, output a short target description "
            "and include one strict JSON object with keys x, y, yaw in map frame. "
            "If the instruction matches a known object in the memory, use its exact coordinates. "
            f"User instruction: {instruction}"
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": raw_image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

        text = self._processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self._processor(
            text=[text],
            images=[raw_image],
            padding=True,
            return_tensors="pt",
        )
        inputs = _move_inputs_for_auto_device(inputs, self._model)

        generated_ids = self._model.generate(
            **inputs,
            max_new_tokens=self.max_new_tokens,
        )
        output = self._processor.batch_decode(generated_ids, skip_special_tokens=True)
        return output[0].split("assistant\n")[-1] if "assistant\n" in output[0] else output[0]

    def _infer_via_subprocess(self, instruction: str, image_path: str) -> str:
        if not os.path.exists(self.inference_script_path):
            raise FileNotFoundError(
                f"Inference script not found: {self.inference_script_path}"
            )

        cmd = [
            "conda",
            "run",
            "-n",
            self.conda_env,
            "python",
            self.inference_script_path,
            "--model-path",
            self.model_path,
            "--image-path",
            image_path,
            "--instruction",
            instruction,
            "--max-new-tokens",
            str(self.max_new_tokens),
            "--force-cpu",
        ]

        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = "-1"
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, env=env)
        if proc.returncode != 0:
            stderr = proc.stderr.strip() if proc.stderr else "No stderr"
            raise RuntimeError(f"Subprocess inference failed: {stderr}")

        output = proc.stdout.strip()
        if not output:
            raise RuntimeError("Subprocess inference returned empty output.")
        return output

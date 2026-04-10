import os
from typing import Optional

from PIL import Image
import torch
from transformers import AutoProcessor, BitsAndBytesConfig, Qwen3VLForConditionalGeneration


class QwenVLWrapper:
    """Local Qwen3-VL wrapper with lazy loading for Node 5."""

    def __init__(self, model_path: str, max_new_tokens: int = 256) -> None:
        self.model_path = model_path
        self.max_new_tokens = max_new_tokens
        self._model = None
        self._processor = None

    def _ensure_loaded(self) -> None:
        if self._model is not None and self._processor is not None:
            return

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model path not found: {self.model_path}")

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )

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
        self._ensure_loaded()

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image path not found: {image_path}")

        raw_image = Image.open(image_path).convert("RGB")

        prompt = (
            "You are a warehouse navigation assistant. "
            "Given the user instruction and scene image, output a short target description "
            "and include one strict JSON object with keys x, y, yaw in map frame if possible. "
            "If exact coordinates are uncertain, still provide your best guess. "
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
        ).to("cuda")

        generated_ids = self._model.generate(
            **inputs,
            max_new_tokens=self.max_new_tokens,
        )
        output = self._processor.batch_decode(generated_ids, skip_special_tokens=True)
        return output[0].split("assistant\n")[-1] if "assistant\n" in output[0] else output[0]

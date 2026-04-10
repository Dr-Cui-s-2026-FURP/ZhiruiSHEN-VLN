import torch
from transformers import Qwen3VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from PIL import Image
import os

# ==========================================
# 1. 路径与配置
# ==========================================
MODEL_PATH = "/home/bluepoisons/Desktop/FURP/VLN/models/Qwen3-VL-2B-Instruct"
# 你可以换成仓库里的任何一张图：chair_photo1.png, plant_photo1.png, warehouse_photo1.png
IMAGE_PATH = "/home/bluepoisons/Desktop/FURP/VLN/ZhiruiSHEN-VLN/data/test_samples/warehouse_photo1.png"

# 4-bit 量化配置：降低显存占用
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True
)

# ==========================================
# 2. 模型加载
# ==========================================
print("正在加载 Qwen3-VL-2B-Instruct...")
try:
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        MODEL_PATH,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )
    processor = AutoProcessor.from_pretrained(MODEL_PATH, trust_remote_code=True)
    print("模型加载成功。")
except Exception as e:
    print(f"加载失败，请检查路径或环境：{e}")
    exit()

# ==========================================
# 3. 图像预处理 (修复 Padding 报错的关键)
# ==========================================
if not os.path.exists(IMAGE_PATH):
    print(f"找不到图片文件：{IMAGE_PATH}")
    exit()

# 使用 PIL 手动加载，避开 transformers 对路径字符串的解析问题
raw_image = Image.open(IMAGE_PATH).convert("RGB")

# 构造符合 VLN 场景的 Prompt
messages = [
    {
        "role": "user",
        "content": [
            {"type": "image", "image": raw_image},
            {"type": "text", "text": "You are a warehouse navigation assistant. Looking at the image, please describe the spatial relationship between the white robot, the black office chair, and the potted plant on the floor. Also, locate the purple boxes on the shelves."}
        ],
    }
]

# ==========================================
# 4. 执行推理
# ==========================================
print("正在进行视觉推理，请稍候...")
text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

# 这里的 images= [raw_image] 是关键，直接传对象不传路径
inputs = processor(
    text=[text], 
    images=[raw_image], 
    padding=True, 
    return_tensors="pt"
).to("cuda")

# 生成配置：max_new_tokens 决定了描述的长短
generated_ids = model.generate(**inputs, max_new_tokens=256)
output_text = processor.batch_decode(generated_ids, skip_special_tokens=True)

print("\n" + "="*30)
print("视觉理解结果：")
print("-" * 30)
# 提取模型生成的回答部分
print(output_text[0].split("assistant\n")[-1] if "assistant\n" in output_text[0] else output_text[0])
print("="*30)
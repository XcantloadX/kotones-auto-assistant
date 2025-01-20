from transformers import AutoModelForCausalLM, AutoTokenizer
import gradio as gr
from PIL import Image
import torch
import numpy as np
from PIL import ImageDraw

# 加载模型
model_id = "vikhyatk/moondream2"
revision = "2025-01-09"  # Pin to specific version

def load_model():
    model = AutoModelForCausalLM.from_pretrained(
        model_id, trust_remote_code=True, revision=revision,
        torch_dtype=torch.float16, device_map={"": "cuda"}
    ).to("cuda")
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
    return model, tokenizer

model, tokenizer = load_model()
print('Model loaded successfully')

def answer_question(image, question):
    enc_image = model.encode_image(image)
    answer = model.answer_question(enc_image, question, tokenizer)
    return answer

def generate_caption(image, length="normal"):
    result = model.caption(image, length=length)
    return result["caption"]

def visual_query(image, query):
    result = model.query(image, query)
    return result["answer"]

def detect_objects(image, object_type):
    # 获取检测结果
    result = model.detect(image, object_type)
    objects = result["objects"]
    print("Detection result:", result)  # 添加调试信息
    
    # 在图像上标注检测结果
    img_draw = image.copy()
    draw = ImageDraw.Draw(img_draw)
    width, height = image.size
    
    # 为每个检测到的对象画框
    for obj in objects:
        # 将相对坐标转换为像素坐标
        x_min = int(float(obj['x_min']) * width)
        y_min = int(float(obj['y_min']) * height)
        x_max = int(float(obj['x_max']) * width)
        y_max = int(float(obj['y_max']) * height)
        box = [x_min, y_min, x_max, y_max]
        print(f"Object box (pixels): {box}")  # 添加每个对象的框信息
        draw.rectangle(box, outline="red", width=3)
    
    # 返回详细的检测结果
    result_text = f"Found {len(objects)} {object_type}(s)\n"
    for i, obj in enumerate(objects, 1):
        result_text += f"Object {i}: x={obj['x_min']:.3f}-{obj['x_max']:.3f}, y={obj['y_min']:.3f}-{obj['y_max']:.3f}\n"
    return result_text, img_draw

def point_objects(image, object_type):
    # 获取点定位结果
    result = model.point(image, object_type)
    points = result["points"]
    print("Points result:", points)  # 添加调试信息
    
    # 在图像上标注点
    img_draw = image.copy()
    draw = ImageDraw.Draw(img_draw)
    width, height = image.size
    
    # 为每个点画圆
    result_text = f"Found {len(points)} {object_type}(s)\n"
    for i, point in enumerate(points, 1):
        if isinstance(point, dict) and 'x' in point and 'y' in point:
            # 坐标是相对值（0-1），需要转换为实际像素坐标
            x = int(float(point['x']) * width)
            y = int(float(point['y']) * height)
            result_text += f"Point {i}: x={point['x']:.3f}, y={point['y']:.3f}\n"
            
            radius = 10
            draw.ellipse([x-radius, y-radius, x+radius, y+radius], fill="red")
        else:
            print(f"Unexpected point format: {point}")
            result_text += f"Point {i}: Invalid format\n"
    
    return result_text, img_draw

# 创建 Gradio 界面
with gr.Blocks() as demo:
    gr.Markdown("# Moondream2 视觉分析演示")
    
    with gr.Tab("问答"):
        with gr.Row():
            image_input1 = gr.Image(type="pil", label="上传图片")
            question_input = gr.Textbox(label="输入问题")
        answer_output = gr.Textbox(label="回答")
        answer_button = gr.Button("获取回答")
        answer_button.click(answer_question, inputs=[image_input1, question_input], outputs=answer_output)
    
    with gr.Tab("图像描述"):
        with gr.Row():
            image_input2 = gr.Image(type="pil", label="上传图片")
            length_input = gr.Radio(["short", "normal"], label="描述长度", value="normal")
        caption_output = gr.Textbox(label="描述结果")
        caption_button = gr.Button("生成描述")
        caption_button.click(generate_caption, inputs=[image_input2, length_input], outputs=caption_output)
    
    with gr.Tab("视觉查询"):
        with gr.Row():
            image_input3 = gr.Image(type="pil", label="上传图片")
            query_input = gr.Textbox(label="输入查询")
        query_output = gr.Textbox(label="查询结果")
        query_button = gr.Button("执行查询")
        query_button.click(visual_query, inputs=[image_input3, query_input], outputs=query_output)
    
    with gr.Tab("物体检测"):
        with gr.Row():
            image_input4 = gr.Image(type="pil", label="上传图片")
            object_input = gr.Textbox(label="输入要检测的物体类型")
        with gr.Row():
            detect_text_output = gr.Textbox(label="检测结果")
            detect_image_output = gr.Image(type="pil", label="可视化结果")
        detect_button = gr.Button("开始检测")
        detect_button.click(detect_objects, inputs=[image_input4, object_input], outputs=[detect_text_output, detect_image_output])
    
    with gr.Tab("点定位"):
        with gr.Row():
            image_input5 = gr.Image(type="pil", label="上传图片")
            point_object_input = gr.Textbox(label="输入要定位的物体类型")
        with gr.Row():
            point_text_output = gr.Textbox(label="定位结果")
            point_image_output = gr.Image(type="pil", label="可视化结果")
        point_button = gr.Button("开始定位")
        point_button.click(point_objects, inputs=[image_input5, point_object_input], outputs=[point_text_output, point_image_output])

demo.launch(share=True)
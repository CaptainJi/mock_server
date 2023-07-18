#! /usr/bin/env python
# -- coding: utf-8 --
"""
-*- coding: UTF-8 -*-
Project   : mock_server
Author    : Captain
Email     : qing.ji@extremevision.com.cn
Date      : 2023/6/9 11:51
FileName  : test.py
Software  : PyCharm
Desc      :
"""
import json
import os
import jinja2
import uvicorn
import yaml
from fastapi import APIRouter, Depends, FastAPI, Request
from loguru import logger
from fastapi import File, UploadFile  # 导入File和UploadFile

logger.add("log/runtime_{time}.log", rotation="500 MB")

app = FastAPI()
router = APIRouter()
folder_path = os.path.join("./mock_data")
mock_list = []

for root, dirs, files in os.walk(folder_path):
    for file in files:
        file_path = os.path.join(root, file)
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            mock_list.append(data)

# 定义一个jinja2环境对象，用于渲染yaml文件
env = jinja2.Environment(loader=jinja2.FileSystemLoader(folder_path))


# 定义一个异步依赖函数，用于匹配请求和返回响应
async def mock_response(request: Request):
    # 获取请求的url、请求头，请求体等信息
    url = request.url.path
    headers = request.headers
    # 根据请求头中的Content-Type来获取请求体
    content_type = request.headers.get("Content-Type")
    if content_type is None:
        body = {}  # 使用request.headers.get("Content-Type")来获取Content-Type的值
    elif content_type == "application/json":
        body = await request.json()
    elif content_type == "application/x-www-form-urlencoded":
        body = await request.form()
        # 把form-data转换成字典
        body = dict(body)
    elif content_type.startswith("multipart/form-data"):  # 判断content_type是否以multipart/form-data开头
        # 如果是multipart/form-data格式，直接使用request.form()来获取表单数据
        body = await request.form()
        # 把form-data转换成字典，键为name属性，值为content属性或UploadFile对象（根据类型判断）
        body = dict(body)
        # 如果file参数是一个UploadFile对象，调用它的read()方法来获取文件内容，并转换成bytes类型
        if "file" in body and isinstance(body["file"], UploadFile):  # 判断body中是否有file这个键，再判断它的类型
            body["file"] = bytes(await body["file"].read())

    else:
        # 获取原始的请求体
        body = await request.body()
        # 把bytes类型的请求体转换成字符串
        body = body.decode()
        # 把字符串类型的请求体转换成字典
        body = json.loads(body)

    # 从列表中获取对应的yaml文件内容，如果yaml中的path键值与url中的接口地址匹配则返回yaml文件中的response
    for item in mock_list:
        if item["path"] == url:
            logger.info(f"请求path：{url}")
            logger.info(f"请求headers：{headers}")
            logger.info(f"请求body：{body}")
            # 渲染yaml文件，替换变量为实际值，并添加扩展名
            template = env.get_template(url + ".yml")
            rendered_data = yaml.safe_load(template.render(**body))
            logger.debug(template.render(**body))
            # 返回对应的响应体部分，并跳出循环
            logger.info(f'返回体：{rendered_data["response"]}')
            return rendered_data["response"]
    # 如果没有找到对应的url，返回错误信息
    logger.info(f"请求path：{url}")
    logger.info(f"请求headers：{headers}")
    logger.info(f"请求body：{body}")
    return {"error": "No mock data found"}


# 定义一个通用路由，接收任意请求，使用依赖函数来处理
@router.get("/{path:path}")
@router.post("/{path:path}")
@router.put("/{path:path}")
@router.delete("/{path:path}")
async def mock_server(request: Request, response: dict = Depends(mock_response)):
    # 使用jsonable_encoder来处理响应体，避免出现不可序列化的对象
    from fastapi.encoders import jsonable_encoder
    return jsonable_encoder(response)


# 将路由对象添加到web应用中
app.include_router(router)

# 使用uvicorn来运行web应用，监听8000端口
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8888,log_level='info')

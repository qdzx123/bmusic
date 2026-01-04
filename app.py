from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import requests
import bili
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route("/")
def home():
    return "BiliMusic No-OSS Server is Running!"

# ================= 代理路由 (核心) =================
@app.route('/proxy')
def proxy_stream():
    """
    流式代理接口。
    前端访问这个接口 -> 后端请求B站 -> 后端返回数据给前端
    这样可以绕过 Referer 防盗链。
    """
    url = request.args.get('url')
    if not url:
        return "Missing URL", 400

    # 伪造 B站需要的 Headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36 Edg/80.0.361.66',
        'Referer': 'https://www.bilibili.com/'
    }

    try:
        # stream=True 意味着不下载整个文件到内存，而是来一点传一点
        req = requests.get(url, headers=headers, stream=True)
        
        # 将 B站的响应头透传给前端 (主要是 Content-Type)
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers_response = [(name, value) for (name, value) in req.headers.items()
                           if name.lower() not in excluded_headers]

        return Response(stream_with_context(req.iter_content(chunk_size=1024*8)),
                        headers=headers_response,
                        content_type=req.headers['Content-Type'],
                        status=req.status_code)
    except Exception as e:
        return f"Proxy Error: {e}", 500

# ================= 业务路由 =================

@app.route('/search/', methods=['GET', 'POST'])
def search_route():
    dic = request.values.to_dict()
    res = bili.handle_search(dic)
    return jsonify(res)

@app.route('/music/', methods=['GET', 'POST'])
def music_route():
    dic = request.values.to_dict()
    
    # 获取当前服务器的完整 URL根路径 (例如 https://my-app.onrender.com/)
    # 必须以 / 结尾
    host_url = request.host_url
    
    # 将 host_url 传给 bili 模块，用于拼接 proxy 地址
    res = bili.handle_music(dic, host_url)
    return jsonify(res)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 9000))
    app.run(host="0.0.0.0", port=port)
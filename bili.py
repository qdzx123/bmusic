# -*- coding: utf-8 -*-
import requests
import json
import html
import urllib.parse

# 基础配置
header = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36 Edg/80.0.361.66',
    'Referer': 'https://www.bilibili.com'
}

# ================= 搜索模块 =================

def remove_em(s):
    s = "".join(s.split("</em>"))
    s = "".join(s.split('<em class="keyword">'))
    s = html.unescape(s)
    return s

def search_bili(keyword, Type, limit, offset):
    typet = {"music": "video", "user": "bili_user"}
    try:
        Type = typet[Type]
    except:
        Type = typet["music"]

    # 页码处理
    page = int(offset) + 1
    url = "https://api.bilibili.com/x/web-interface/search/type?keyword={}&search_type={}&page={}&page_size={}"
    url = url.format(keyword, Type, str(page), limit)
    
    headers = header.copy()
    headers["Cookie"] = "buvid3=infoc;" # 简易Cookie防止搜索报错
    
    try:
        r = requests.get(url, headers=headers)
        data = json.loads(r.text)
        if "data" not in data or "result" not in data["data"]:
            return []
        dic = data["data"]["result"]
    except:
        return []

    res_list = []
    if Type == typet["music"]:
        if not isinstance(dic, list): return []
        for i in dic:
            x = {}
            x['type'] = 'p' 
            x['mid'] = "Bav"+str(i['aid'])
            x['name'] = remove_em(i['title'])
            x['artist'] = [i["author"]]
            x['album'] = {'name': ""}
            res_list.append(x)
    
    return res_list

# ================= 详情与音频获取模块 =================

def get_vid_info(vid):
    if vid.startswith("B"):
        url = f"https://api.bilibili.com/x/web-interface/view?bvid={vid}"
    else:
        url = f"https://api.bilibili.com/x/web-interface/view?aid={vid}"
    r = requests.get(url, headers=header)
    return json.loads(r.text)

def get_audio_url_direct(vid):
    """获取B站原始Dash音频链接"""
    try:
        r = requests.get(f"https://www.bilibili.com/video/{vid}", headers=header)
        s = r.text
        p = s.find("playinfo__=")
        if p == -1: return ""
        s = s[p+11:]
        p = s.find("</script>")
        s = s[:p]
        playinfo = json.loads(s)
        # 获取第一个音频流
        return playinfo["data"]["dash"]["audio"][0]["baseUrl"]
    except:
        return ""

def get_bili_detail(mid, Type, host_url):
    """
    host_url: 当前服务器的地址，用于生成代理链接
    """
    raw_id = mid[1:] # 去掉开头的 B
    
    if Type == "p": # 多P列表
        if "?" in raw_id: raw_id = raw_id.split("?")[0]
        aid = raw_id[2:] # 去掉 av
        
        info = get_vid_info(aid).get('data', {})
        if not info: return []

        res = []
        for page in info.get('pages', []):
            x = {}
            x["type"] = "music"
            x["name"] = info['title'] + "-" + page["part"]
            x["mid"] = f"Bav{info['aid']}_{page['page']}"
            x["artist"] = [info["owner"]["name"]]
            x["album"] = {"name": ""}
            res.append(x)
        return res

    elif Type == "music": # 单曲详情
        if "_" not in raw_id: raw_id += "_1"
        parts = raw_id.split("_")
        vid_base = parts[0] # av12345
        p_index = int(parts[1])
        aid = vid_base[2:] 

        info = get_vid_info(aid).get('data', {})
        if not info: return {}
        
        # 1. 获取B站原始音频链接
        original_url = get_audio_url_direct(f"{vid_base}?p={p_index}")
        
        # 2. 生成代理链接 (关键步骤)
        # 如果获取不到链接，就留空
        if original_url:
            # 将原始链接编码，拼接到我们自己的 proxy 接口后面
            encoded_url = urllib.parse.quote(original_url)
            # 最终 src 类似于: http://my-server.com/proxy?url=http://bili...
            src = f"{host_url}proxy?url={encoded_url}"
        else:
            src = ""

        page_part = info['pages'][min(p_index, len(info['pages']))-1]['part']
        
        dic = {
            "type": "music",
            "mid": "B" + raw_id,
            "src": src, # 这里返回的是代理地址
            "img": info['pic'], # 图片B站一般不防盗链，由于太麻烦，直接用原始的试一试
            "lrc": "[00:00.00]暂无歌词",
            "album": {"name": ""},
            "artist": [info['owner']['name']],
            "name": f"{info['title']} - {page_part}"
        }
        return dic
        
    return []

# 入口函数
def handle_search(dic):
    return search_bili(dic.get('keyword', ''), dic.get('type', 'music'), dic.get('limit', '20'), dic.get('offset', '0'))

def handle_music(dic, host_url):
    mid = dic.get('mid', '')
    if mid.startswith("B"):
        return get_bili_detail(mid, dic.get('type', 'music'), host_url)
    return {}
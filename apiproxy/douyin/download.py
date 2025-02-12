#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import json
import time
import requests
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from typing import List, Optional
from pathlib import Path
# import asyncio  # 暂时注释掉
# import aiohttp  # 暂时注释掉
import logging

from apiproxy.douyin import douyin_headers
from apiproxy.common import utils

logger = logging.getLogger("douyin_downloader")

class Download(object):
    def __init__(self, thread=5, music=True, cover=True, avatar=True, resjson=True, folderstyle=True):
        self.thread = thread
        self.music = music
        self.cover = cover
        self.avatar = avatar
        self.resjson = resjson
        self.folderstyle = folderstyle

    def progressBarDownload(self, url, filepath, desc):
        response = requests.get(url, stream=True, headers=douyin_headers)
        chunk_size = 1024  # 每次下载的数据大小
        content_size = int(response.headers['content-length'])  # 下载文件总大小
        try:
            if response.status_code == 200:  # 判断是否响应成功
                with open(filepath, 'wb') as file, tqdm(total=content_size,
                                                        unit="iB",
                                                        desc=desc,
                                                        unit_scale=True,
                                                        unit_divisor=1024,

                                                        ) as bar:  # 显示进度条
                    for data in response.iter_content(chunk_size=chunk_size):
                        size = file.write(data)
                        bar.update(size)
        except Exception as e:
            # 下载异常 删除原来下载的文件, 可能未下成功
            if os.path.exists(filepath):
                os.remove(filepath)
            print("[  错误  ]:下载出错\r")

    def _download_media(self, url: str, path: Path, desc: str) -> bool:
        """通用下载方法，处理所有类型的媒体下载"""
        if path.exists():
            logger.info(f"文件已存在，跳过下载: {path}")
            return True
            
        try:
            response = requests.get(url, stream=True, headers=douyin_headers)
            if response.status_code != 200:
                logger.error(f"下载失败，状态码: {response.status_code}, URL: {url}")
                return False
                
            total_size = int(response.headers.get('content-length', 0))
            with open(path, 'wb') as file, tqdm(
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
                desc=desc
            ) as bar:
                for data in response.iter_content(chunk_size=1024):
                    size = file.write(data)
                    bar.update(size)
            return True
            
        except Exception as e:
            logger.error(f"下载出错: {url} 错误: {str(e)}")
            if path.exists():
                path.unlink()
            return False

    def awemeDownload(self, awemeDict: dict, savePath: Path) -> None:
        """下载单个作品的所有内容"""
        if not awemeDict:
            logger.warning("无效的作品数据")
            return
            
        try:
            # 创建保存目录
            save_path = Path(savePath)
            save_path.mkdir(parents=True, exist_ok=True)
            
            # 构建文件名
            file_name = f"{awemeDict['create_time']}_{utils.replaceStr(awemeDict['desc'])}"
            aweme_path = save_path / file_name if self.folderstyle else save_path
            aweme_path.mkdir(exist_ok=True)
            
            # 保存JSON数据
            if self.resjson:
                self._save_json(aweme_path / f"{file_name}_result.json", awemeDict)
                
            # 下载媒体文件
            desc = file_name[:30]
            self._download_media_files(awemeDict, aweme_path, file_name, desc)
                
        except Exception as e:
            logger.error(f"处理作品时出错: {str(e)}")

    def _save_json(self, path: Path, data: dict) -> None:
        """保存JSON数据"""
        try:
            with open(path, "w", encoding='utf-8') as f:
                json.dump(data, ensure_ascii=False, indent=2, fp=f)
        except Exception as e:
            logger.error(f"保存JSON失败: {path}, 错误: {str(e)}")

    def _download_media_files(self, aweme: dict, path: Path, name: str, desc: str) -> None:
        """下载所有媒体文件"""
        # 下载视频或图集
        if aweme["awemeType"] == 0:  # 视频
            video_path = path / f"{name}_video.mp4"
            if url := aweme.get("video", {}).get("play_addr", {}).get("url_list", [None])[0]:
                self._download_media(url, video_path, f"[视频]{desc}")
        elif aweme["awemeType"] == 1:  # 图集
            for i, image in enumerate(aweme.get("images", [])):
                if url := image.get("url_list", [None])[0]:
                    image_path = path / f"{name}_image_{i}.jpeg"
                    self._download_media(url, image_path, f"[图集]{desc}")

        # 下载音乐
        if self.music and (url := aweme.get("music", {}).get("play_url", {}).get("url_list", [None])[0]):
            music_name = utils.replaceStr(aweme["music"]["title"])
            music_path = path / f"{name}_music_{music_name}.mp3"
            self._download_media(url, music_path, f"[音乐]{desc}")

        # 下载封面
        if self.cover and aweme["awemeType"] == 0:
            if url := aweme.get("video", {}).get("cover", {}).get("url_list", [None])[0]:
                cover_path = path / f"{name}_cover.jpeg"
                self._download_media(url, cover_path, f"[封面]{desc}")

        # 下载头像
        if self.avatar:
            if url := aweme.get("author", {}).get("avatar", {}).get("url_list", [None])[0]:
                avatar_path = path / f"{name}_avatar.jpeg"
                self._download_media(url, avatar_path, f"[头像]{desc}")

    def userDownload(self, awemeList: List[dict], savePath: Path):
        if awemeList is None:
            return
        if not os.path.exists(savePath):
            os.mkdir(savePath)

        self.alltask = []
        self.pool = ThreadPoolExecutor(max_workers=self.thread)

        start = time.time()  # 开始时间

        with tqdm(total=len(awemeList), desc="下载进度") as pbar:
            for aweme in awemeList:
                self.awemeDownload(awemeDict=aweme, savePath=savePath)
                pbar.update(1)

        wait(self.alltask, return_when=ALL_COMPLETED)

        # 检查下载是否完成
        while True:
            print("[  提示  ]:正在检查下载是否完成...")
            self.isdwownload = True
            # 下载上一步失败的
            for aweme in awemeList:
                self.awemeDownload(awemeDict=aweme, savePath=savePath)

            wait(self.alltask, return_when=ALL_COMPLETED)

            if self.isdwownload:
                break

        end = time.time()  # 结束时间
        print('\n' + '[下载完成]:耗时: %d分钟%d秒\n' % (int((end - start) / 60), ((end - start) % 60)))  # 输出下载用时时间

    # 暂时注释掉异步下载相关的方法
    '''
    async def download_file(self, url: str, path: Path) -> bool:
        """异步下载单个文件"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        with open(path, 'wb') as f:
                            f.write(await response.read())
                        return True
                    else:
                        logger.error(f"下载失败: {url}, 状态码: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"下载出错: {url}, 错误: {str(e)}")
            return False

    async def batch_download(self, urls: List[str], paths: List[Path]):
        """批量异步下载"""
        tasks = [self.download_file(url, path) 
                for url, path in zip(urls, paths)]
        results = await asyncio.gather(*tasks)
        return all(results)
    '''


if __name__ == "__main__":
    pass

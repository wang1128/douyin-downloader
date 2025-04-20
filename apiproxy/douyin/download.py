#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import json
import time
import traceback

import requests
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from typing import List, Optional
from pathlib import Path
# import asyncio  # 暂时注释掉
# import aiohttp  # 暂时注释掉
import logging
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint

from apiproxy.douyin import douyin_headers
from apiproxy.common import utils

logger = logging.getLogger("douyin_downloader")
console = Console()

class Download(object):
    def __init__(self, thread=5, music=True, cover=True, avatar=True, resjson=True, folderstyle=True):
        self.thread = thread
        self.music = music
        self.cover = cover
        self.avatar = avatar
        self.resjson = resjson
        self.folderstyle = folderstyle
        self.console = Console()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            transient=True  # 添加这个参数，进度条完成后自动消失
        )
        self.retry_times = 3
        self.chunk_size = 8192
        self.timeout = 30

    def _download_media(self, url: str, path: Path, desc: str) -> bool:
        """通用下载方法，处理所有类型的媒体下载"""
        if path.exists():
            self.console.print(f"[cyan]⏭️  跳过已存在: {desc}[/]")
            return True
            
        # 使用新的断点续传下载方法替换原有的下载逻辑
        return self.download_with_resume(url, path, desc)

    def _download_media_files(self, aweme: dict, path: Path, name: str, desc: str) -> None:
        """下载所有媒体文件"""
        try:
            # 下载视频或图集
            if aweme["awemeType"] == 0:  # 视频
                video_path = path / f"{name}_video.mp4"
                # 安全获取视频URL（网页1[1,3](@ref)）
                video_url = aweme.get("video", {}).get("play_addr", {}).get("url_list", [])[:1]
                if video_url and self._download_media(video_url[0], video_path, f"[视频]{desc}"):
                    pass
                else:
                    self.console.print(f"[yellow]⚠️  视频下载失败: {desc}[/]")

            elif aweme["awemeType"] == 1:  # 图集
                for i, image in enumerate(aweme.get("images", [])):
                    # 使用安全切片获取URL（网页4[4,5](@ref)）
                    image_url = image.get("url_list", [])[:1]
                    if image_url:
                        image_path = path / f"{name}_image_{i}.jpeg"
                        if not self._download_media(image_url[0], image_path, f"[图集{i + 1}]{desc}"):
                            self.console.print(f"[yellow]⚠️  图片{i + 1}下载失败: {desc}[/]")

            # 优化音乐下载逻辑（网页2[2,7](@ref)）
            if self.music:
                music_data = aweme.get("music", {})
                # 安全获取URL列表首个元素
                url_list = music_data.get("play_url", {}).get("url_list", [])
                if url_list:  # 检查列表非空（网页3[3](@ref)）
                    music_name = utils.replaceStr(music_data.get("title", "unknown"))
                    music_path = path / f"{name}_music_{music_name}.mp3"
                    if not self._download_media(url_list[0], music_path, f"[音乐]{desc}"):
                        self.console.print(f"[yellow]⚠️  音乐下载失败: {desc}[/]")

            # 优化封面下载逻辑（同理处理其他模块）
            if self.cover and aweme["awemeType"] == 0:
                cover_url = aweme.get("video", {}).get("cover", {}).get("url_list", [])[:1]
                if cover_url:
                    cover_path = path / f"{name}_cover.jpeg"
                    if not self._download_media(cover_url[0], cover_path, f"[封面]{desc}"):
                        self.console.print(f"[yellow]⚠️  封面下载失败: {desc}[/]")

            # 优化头像下载逻辑
            if self.avatar:
                avatar_url = aweme.get("author", {}).get("avatar", {}).get("url_list", [])[:1]
                if avatar_url:
                    avatar_path = path / f"{name}_avatar.jpeg"
                    if not self._download_media(avatar_url[0], avatar_path, f"[头像]{desc}"):
                        self.console.print(f"[yellow]⚠️  头像下载失败: {desc}[/]")

        except Exception as e:
            traceback.print_exc()
            self.console.print(f"[red]⚠️  发生未捕获异常: {str(e)}[/]")  # 改为警告而非终止

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

    def userDownload(self, awemeList: List[dict], savePath: Path):
        if not awemeList:
            self.console.print("[yellow]⚠️  没有找到可下载的内容[/]")
            return

        save_path = Path(savePath)
        save_path.mkdir(parents=True, exist_ok=True)

        start_time = time.time()
        total_count = len(awemeList)
        success_count = 0
        
        # 显示下载信息面板
        self.console.print(Panel(
            Text.assemble(
                ("下载配置\n", "bold cyan"),
                (f"总数: {total_count} 个作品\n", "cyan"),
                (f"线程: {self.thread}\n", "cyan"),
                (f"保存路径: {save_path}\n", "cyan"),
            ),
            title="抖音下载器",
            border_style="cyan"
        ))

        with self.progress:
            download_task = self.progress.add_task(
                "[cyan]📥 批量下载进度", 
                total=total_count
            )
            
            for aweme in awemeList:
                try:
                    self.awemeDownload(awemeDict=aweme, savePath=save_path)
                    success_count += 1
                    self.progress.update(download_task, advance=1)
                except Exception as e:
                    self.console.print(f"[red]❌ 下载失败: {str(e)}[/]")

        # 显示下载完成统计
        end_time = time.time()
        duration = end_time - start_time
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        
        self.console.print(Panel(
            Text.assemble(
                ("下载完成\n", "bold green"),
                (f"成功: {success_count}/{total_count}\n", "green"),
                (f"用时: {minutes}分{seconds}秒\n", "green"),
                (f"保存位置: {save_path}\n", "green"),
            ),
            title="下载统计",
            border_style="green"
        ))

    def download_with_resume(self, url: str, filepath: Path, desc: str) -> bool:
        """支持断点续传的下载方法"""
        file_size = filepath.stat().st_size if filepath.exists() else 0
        headers = {'Range': f'bytes={file_size}-'} if file_size > 0 else {}
        
        for attempt in range(self.retry_times):
            try:
                response = requests.get(url, headers={**douyin_headers, **headers}, 
                                     stream=True, timeout=self.timeout)
                
                if response.status_code not in (200, 206):
                    raise Exception(f"HTTP {response.status_code}")
                    
                total_size = int(response.headers.get('content-length', 0)) + file_size
                mode = 'ab' if file_size > 0 else 'wb'
                
                with self.progress:
                    task = self.progress.add_task(f"[cyan]⬇️  {desc}", total=total_size)
                    self.progress.update(task, completed=file_size)  # 更新断点续传的进度
                    
                    with open(filepath, mode) as f:
                        for chunk in response.iter_content(chunk_size=self.chunk_size):
                            if chunk:
                                size = f.write(chunk)
                                self.progress.update(task, advance=size)
                                
                return True
                
            except Exception as e:
                logger.warning(f"下载失败 (尝试 {attempt + 1}/{self.retry_times}): {str(e)}")
                if attempt == self.retry_times - 1:
                    self.console.print(f"[red]❌ 下载失败: {desc}\n   {str(e)}[/]")
                    return False
                time.sleep(1)  # 重试前等待


class DownloadManager:
    def __init__(self, max_workers=3):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def download_with_resume(self, url, filepath, callback=None):
        # 检查是否存在部分下载的文件
        file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        
        headers = {'Range': f'bytes={file_size}-'}
        
        response = requests.get(url, headers=headers, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        mode = 'ab' if file_size > 0 else 'wb'
        
        with open(filepath, mode) as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    if callback:
                        callback(len(chunk))


if __name__ == "__main__":
    pass

import pytest
from pathlib import Path
import asyncio
from apiproxy.douyin.download import Download

@pytest.fixture
def downloader():
    return Download(thread=1)

def test_progress_bar_download(downloader, tmp_path):
    test_file = tmp_path / "test.mp4"
    result = downloader.progressBarDownload(
        "https://test-video-url.com/video.mp4",
        test_file,
        "测试下载"
    )
    assert result == True
    assert test_file.exists()

@pytest.mark.asyncio
async def test_async_download(downloader, tmp_path):
    urls = ["https://test1.com/1.mp4", "https://test2.com/2.mp4"]
    paths = [tmp_path / "1.mp4", tmp_path / "2.mp4"]
    
    result = await downloader.batch_download(urls, paths)
    assert result == True
    assert all(p.exists() for p in paths) 
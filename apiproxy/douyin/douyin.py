#!/usr/bin/env python
# -*- coding: utf-8 -*-


import re
import requests
import json
import time
import copy
# from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Tuple, Optional
from requests.exceptions import RequestException
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.console import Console

from apiproxy.douyin import douyin_headers
from apiproxy.douyin.urls import Urls
from apiproxy.douyin.result import Result
from apiproxy.douyin.database import DataBase
from apiproxy.common import utils
from utils import logger

# 创建全局console实例
console = Console()

class Douyin(object):

    def __init__(self, database=False):
        self.urls = Urls()
        self.result = Result()
        self.database = database
        if database:
            self.db = DataBase()
        # 用于设置重复请求某个接口的最大时间
        self.timeout = 10
        self.console = Console()  # 也可以在实例中创建console

    # 从分享链接中提取网址
    def getShareLink(self, string):
        # findall() 查找匹配正则表达式的字符串
        return re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', string)[0]

    # 得到 作品id 或者 用户id
    # 传入 url 支持 https://www.iesdouyin.com 与 https://v.douyin.com
    def getKey(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """获取资源标识
        Args:
            url: 抖音分享链接或网页URL
        Returns:
            (资源类型, 资源ID)
        """
        key = None
        key_type = None

        try:
            r = requests.get(url=url, headers=douyin_headers)
        except Exception as e:
            print('[  错误  ]:输入链接有误！\r')
            return key_type, key

        # 抖音把图集更新为note
        # 作品 第一步解析出来的链接是share/video/{aweme_id}
        # https://www.iesdouyin.com/share/video/7037827546599263488/?region=CN&mid=6939809470193126152&u_code=j8a5173b&did=MS4wLjABAAAA1DICF9-A9M_CiGqAJZdsnig5TInVeIyPdc2QQdGrq58xUgD2w6BqCHovtqdIDs2i&iid=MS4wLjABAAAAomGWi4n2T0H9Ab9x96cUZoJXaILk4qXOJlJMZFiK6b_aJbuHkjN_f0mBzfy91DX1&with_sec_did=1&titleType=title&schema_type=37&from_ssr=1&utm_source=copy&utm_campaign=client_share&utm_medium=android&app=aweme
        # 用户 第一步解析出来的链接是share/user/{sec_uid}
        # https://www.iesdouyin.com/share/user/MS4wLjABAAAA06y3Ctu8QmuefqvUSU7vr0c_ZQnCqB0eaglgkelLTek?did=MS4wLjABAAAA1DICF9-A9M_CiGqAJZdsnig5TInVeIyPdc2QQdGrq58xUgD2w6BqCHovtqdIDs2i&iid=MS4wLjABAAAAomGWi4n2T0H9Ab9x96cUZoJXaILk4qXOJlJMZFiK6b_aJbuHkjN_f0mBzfy91DX1&with_sec_did=1&sec_uid=MS4wLjABAAAA06y3Ctu8QmuefqvUSU7vr0c_ZQnCqB0eaglgkelLTek&from_ssr=1&u_code=j8a5173b&timestamp=1674540164&ecom_share_track_params=%7B%22is_ec_shopping%22%3A%221%22%2C%22secuid%22%3A%22MS4wLjABAAAA-jD2lukp--I21BF8VQsmYUqJDbj3FmU-kGQTHl2y1Cw%22%2C%22enter_from%22%3A%22others_homepage%22%2C%22share_previous_page%22%3A%22others_homepage%22%7D&utm_source=copy&utm_campaign=client_share&utm_medium=android&app=aweme
        # 合集
        # https://www.douyin.com/collection/7093490319085307918
        urlstr = str(r.request.path_url)

        if "/user/" in urlstr:
            # 获取用户 sec_uid
            if '?' in r.request.path_url:
                for one in re.finditer(r'user\/([\d\D]*)([?])', str(r.request.path_url)):
                    key = one.group(1)
            else:
                for one in re.finditer(r'user\/([\d\D]*)', str(r.request.path_url)):
                    key = one.group(1)
            key_type = "user"
        elif "/video/" in urlstr:
            # 获取作品 aweme_id
            key = re.findall('video/(\d+)?', urlstr)[0]
            key_type = "aweme"
        elif "/note/" in urlstr:
            # 获取note aweme_id
            key = re.findall('note/(\d+)?', urlstr)[0]
            key_type = "aweme"
        elif "/mix/detail/" in urlstr:
            # 获取合集 id
            key = re.findall('/mix/detail/(\d+)?', urlstr)[0]
            key_type = "mix"
        elif "/collection/" in urlstr:
            # 获取合集 id
            key = re.findall('/collection/(\d+)?', urlstr)[0]
            key_type = "mix"
        elif "/music/" in urlstr:
            # 获取原声 id
            key = re.findall('music/(\d+)?', urlstr)[0]
            key_type = "music"
        elif "/webcast/reflow/" in urlstr:
            key1 = re.findall('reflow/(\d+)?', urlstr)[0]
            url = self.urls.LIVE2 + utils.getXbogus(
                f'live_id=1&room_id={key1}&app_id=1128')
            res = requests.get(url, headers=douyin_headers)
            resjson = json.loads(res.text)
            key = resjson['data']['room']['owner']['web_rid']
            key_type = "live"
        elif "live.douyin.com" in r.url:
            key = r.url.replace('https://live.douyin.com/', '')
            key_type = "live"

        if key is None or key_type is None:
            print('[  错误  ]:输入链接有误！无法获取 id\r')
            return key_type, key

        return key_type, key

    # 暂时注释掉装饰器
    # @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def getAwemeInfo(self, aweme_id: str) -> dict:
        """获取作品信息（带重试机制）"""
        retries = 3
        for attempt in range(retries):
            try:
                logger.info(f'[  提示  ]:正在请求的作品 id = {aweme_id}')
                if aweme_id is None:
                    return {}

                start = time.time()  # 开始时间
                while True:
                    # 接口不稳定, 有时服务器不返回数据, 需要重新获取
                    try:
                        # 单作品接口返回 'aweme_detail'
                        # 主页作品接口返回 'aweme_list'->['aweme_detail']
                        jx_url = self.urls.POST_DETAIL + utils.getXbogus(
                            f'aweme_id={aweme_id}&device_platform=webapp&aid=6383')

                        raw = requests.get(url=jx_url, headers=douyin_headers).text
                        datadict = json.loads(raw)
                        if datadict is not None and datadict["status_code"] == 0:
                            break
                    except Exception as e:
                        end = time.time()  # 结束时间
                        if end - start > self.timeout:
                            logger.warning(f"重复请求该接口{self.timeout}s, 仍然未获取到数据")
                            return {}


                # 清空self.awemeDict
                self.result.clearDict(self.result.awemeDict)

                # 默认为视频
                awemeType = 0
                try:
                    # datadict['aweme_detail']["images"] 不为 None 说明是图集
                    if datadict['aweme_detail']["images"] is not None:
                        awemeType = 1
                except Exception as e:
                    logger.warning("接口中未找到 images")

                # 转换成我们自己的格式
                self.result.dataConvert(awemeType, self.result.awemeDict, datadict['aweme_detail'])

                return self.result.awemeDict
            except RequestException as e:
                logger.warning(f"请求失败（尝试 {attempt+1}/{retries}）: {str(e)}")
                time.sleep(2 ** attempt)
            except KeyError as e:
                logger.error(f"响应数据格式异常: {str(e)}")
                break
        return {}

    # 传入 url 支持 https://www.iesdouyin.com 与 https://v.douyin.com
    # mode : post | like 模式选择 like为用户点赞 post为用户发布
    def getUserInfo(self, sec_uid, mode="post", count=35, number=0, increase=False, start_time="", end_time=""):
        """获取用户信息
        Args:
            sec_uid: 用户ID
            mode: 模式(post:发布/like:点赞)
            count: 每页数量
            number: 限制下载数量(0表示无限制)
            increase: 是否增量更新
            start_time: 开始时间，格式：YYYY-MM-DD
            end_time: 结束时间，格式：YYYY-MM-DD
        """
        if sec_uid is None:
            return None

        # 处理时间范围
        if end_time == "now":
            end_time = time.strftime("%Y-%m-%d")
        
        if not start_time:
            start_time = "1970-01-01"
        if not end_time:
            end_time = "2099-12-31"

        self.console.print(f"[cyan]🕒 时间范围: {start_time} 至 {end_time}[/]")
        
        max_cursor = 0
        awemeList = []
        total_fetched = 0
        filtered_count = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console,
            transient=True
        ) as progress:
            fetch_task = progress.add_task(
                f"[cyan]📥 正在获取{mode}作品列表...", 
                total=None  # 总数未知，使用无限进度条
            )
            
            while True:
                try:
                    # 构建请求URL
                    if mode == "post":
                        url = self.urls.USER_POST + utils.getXbogus(
                            f'sec_user_id={sec_uid}&count={count}&max_cursor={max_cursor}&device_platform=webapp&aid=6383')
                    elif mode == "like":
                        url = self.urls.USER_FAVORITE_A + utils.getXbogus(
                            f'sec_user_id={sec_uid}&count={count}&max_cursor={max_cursor}&device_platform=webapp&aid=6383')
                    else:
                        self.console.print("[red]❌ 模式选择错误，仅支持post、like[/]")
                        return None

                    # 发送请求
                    res = requests.get(url=url, headers=douyin_headers)
                    datadict = json.loads(res.text)
                    
                    # 处理返回数据
                    if not datadict or datadict.get("status_code") != 0:
                        self.console.print(f"[red]❌ API请求失败: {datadict.get('status_msg', '未知错误')}[/]")
                        break
                        
                    current_count = len(datadict["aweme_list"])
                    total_fetched += current_count
                    
                    # 更新进度显示
                    progress.update(
                        fetch_task, 
                        description=f"[cyan]📥 已获取: {total_fetched}个作品"
                    )

                    # 在处理作品时添加时间过滤
                    for aweme in datadict["aweme_list"]:
                        create_time = time.strftime(
                            "%Y-%m-%d", 
                            time.localtime(int(aweme.get("create_time", 0)))
                        )
                        
                        # 时间过滤
                        if not (start_time <= create_time <= end_time):
                            filtered_count += 1
                            continue

                        # 数量限制检查
                        if number > 0 and len(awemeList) >= number:
                            self.console.print(f"[green]✅ 已达到限制数量: {number}[/]")
                            return awemeList
                            
                        # 增量更新检查
                        if self.database:
                            if mode == "post":
                                if self.db.get_user_post(sec_uid=sec_uid, aweme_id=aweme['aweme_id']):
                                    if increase and aweme['is_top'] == 0:
                                        self.console.print("[green]✅ 增量更新完成[/]")
                                        return awemeList
                                else:
                                    self.db.insert_user_post(sec_uid=sec_uid, aweme_id=aweme['aweme_id'], data=aweme)
                            elif mode == "like":
                                if self.db.get_user_like(sec_uid=sec_uid, aweme_id=aweme['aweme_id']):
                                    if increase and aweme['is_top'] == 0:
                                        self.console.print("[green]✅ 增量更新完成[/]")
                                        return awemeList
                            else:
                                self.console.print("[red]❌ 模式选择错误，仅支持post、like[/]")
                                return None

                        # 转换数据格式
                        aweme_data = self._convert_aweme_data(aweme)
                        if aweme_data:
                            awemeList.append(aweme_data)

                    # 检查是否还有更多数据
                    if not datadict["has_more"]:
                        self.console.print(f"[green]✅ 已获取全部作品: {total_fetched}个[/]")
                        break
                    
                    # 更新游标
                    max_cursor = datadict["max_cursor"]
                    
                except Exception as e:
                    self.console.print(f"[red]❌ 获取作品列表出错: {str(e)}[/]")
                    break

        return awemeList

    def _convert_aweme_data(self, aweme):
        """转换作品数据格式"""
        try:
            self.result.clearDict(self.result.awemeDict)
            aweme_type = 1 if aweme.get("images") else 0
            self.result.dataConvert(aweme_type, self.result.awemeDict, aweme)
            return copy.deepcopy(self.result.awemeDict)
        except Exception as e:
            logger.error(f"数据转换错误: {str(e)}")
            return None

    def getLiveInfo(self, web_rid: str):
        print('[  提示  ]:正在请求的直播间 id = %s\r\n' % web_rid)

        start = time.time()  # 开始时间
        while True:
            # 接口不稳定, 有时服务器不返回数据, 需要重新获取
            try:
                live_api = self.urls.LIVE + utils.getXbogus(
                    f'aid=6383&device_platform=web&web_rid={web_rid}')

                response = requests.get(live_api, headers=douyin_headers)
                live_json = json.loads(response.text)
                if live_json != {} and live_json['status_code'] == 0:
                    break
            except Exception as e:
                end = time.time()  # 结束时间
                if end - start > self.timeout:
                    print("[  提示  ]:重复请求该接口" + str(self.timeout) + "s, 仍然未获取到数据")
                    return {}

        # 清空字典
        self.result.clearDict(self.result.liveDict)

        # 类型
        self.result.liveDict["awemeType"] = 2
        # 是否在播
        self.result.liveDict["status"] = live_json['data']['data'][0]['status']

        if self.result.liveDict["status"] == 4:
            print('[   📺   ]:当前直播已结束，正在退出')
            return self.result.liveDict

        # 直播标题
        self.result.liveDict["title"] = live_json['data']['data'][0]['title']

        # 直播cover
        self.result.liveDict["cover"] = live_json['data']['data'][0]['cover']['url_list'][0]

        # 头像
        self.result.liveDict["avatar"] = live_json['data']['data'][0]['owner']['avatar_thumb']['url_list'][0].replace(
            "100x100", "1080x1080")

        # 观看人数
        self.result.liveDict["user_count"] = live_json['data']['data'][0]['user_count_str']

        # 昵称
        self.result.liveDict["nickname"] = live_json['data']['data'][0]['owner']['nickname']

        # sec_uid
        self.result.liveDict["sec_uid"] = live_json['data']['data'][0]['owner']['sec_uid']

        # 直播间观看状态
        self.result.liveDict["display_long"] = live_json['data']['data'][0]['room_view_stats']['display_long']

        # 推流
        self.result.liveDict["flv_pull_url"] = live_json['data']['data'][0]['stream_url']['flv_pull_url']

        try:
            # 分区
            self.result.liveDict["partition"] = live_json['data']['partition_road_map']['partition']['title']
            self.result.liveDict["sub_partition"] = \
                live_json['data']['partition_road_map']['sub_partition']['partition']['title']
        except Exception as e:
            self.result.liveDict["partition"] = '无'
            self.result.liveDict["sub_partition"] = '无'

        info = '[   💻   ]:直播间：%s  当前%s  主播：%s 分区：%s-%s\r' % (
            self.result.liveDict["title"], self.result.liveDict["display_long"], self.result.liveDict["nickname"],
            self.result.liveDict["partition"], self.result.liveDict["sub_partition"])
        print(info)

        flv = []
        print('[   🎦   ]:直播间清晰度')
        for i, f in enumerate(self.result.liveDict["flv_pull_url"].keys()):
            print('[   %s   ]: %s' % (i, f))
            flv.append(f)

        rate = int(input('[   🎬   ]输入数字选择推流清晰度：'))

        self.result.liveDict["flv_pull_url0"] = self.result.liveDict["flv_pull_url"][flv[rate]]

        # 显示清晰度列表
        print('[   %s   ]:%s' % (flv[rate], self.result.liveDict["flv_pull_url"][flv[rate]]))
        print('[   📺   ]:复制链接使用下载工具下载')
        return self.result.liveDict

    def getMixInfo(self, mix_id, count=35, number=0, increase=False, sec_uid="", start_time="", end_time=""):
        """获取合集信息"""
        if mix_id is None:
            return None

        # 处理时间范围
        if end_time == "now":
            end_time = time.strftime("%Y-%m-%d")
        
        if not start_time:
            start_time = "1970-01-01"
        if not end_time:
            end_time = "2099-12-31"

        self.console.print(f"[cyan]🕒 时间范围: {start_time} 至 {end_time}[/]")

        cursor = 0
        awemeList = []
        total_fetched = 0
        filtered_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console,
            transient=True
        ) as progress:
            fetch_task = progress.add_task(
                "[cyan]📥 正在获取合集作品...",
                total=None
            )

            while True:  # 外层循环
                try:
                    url = self.urls.USER_MIX + utils.getXbogus(
                        f'mix_id={mix_id}&cursor={cursor}&count={count}&device_platform=webapp&aid=6383')

                    res = requests.get(url=url, headers=douyin_headers)
                    datadict = json.loads(res.text)

                    if not datadict:
                        self.console.print("[red]❌ 获取数据失败[/]")
                        break

                    for aweme in datadict["aweme_list"]:
                        create_time = time.strftime(
                            "%Y-%m-%d",
                            time.localtime(int(aweme.get("create_time", 0)))
                        )

                        # 时间过滤
                        if not (start_time <= create_time <= end_time):
                            filtered_count += 1
                            continue

                        # 数量限制检查
                        if number > 0 and len(awemeList) >= number:
                            return awemeList  # 使用return替代break

                        # 增量更新检查
                        if self.database:
                            if self.db.get_mix(sec_uid=sec_uid, mix_id=mix_id, aweme_id=aweme['aweme_id']):
                                if increase and aweme['is_top'] == 0:
                                    return awemeList  # 使用return替代break
                            else:
                                self.db.insert_mix(sec_uid=sec_uid, mix_id=mix_id, aweme_id=aweme['aweme_id'], data=aweme)

                        # 转换数据
                        aweme_data = self._convert_aweme_data(aweme)
                        if aweme_data:
                            awemeList.append(aweme_data)

                    # 检查是否还有更多数据
                    if not datadict.get("has_more"):
                        self.console.print(f"[green]✅ 已获取全部作品[/]")
                        break

                    # 更新游标
                    cursor = datadict.get("cursor", 0)
                    total_fetched += len(datadict["aweme_list"])
                    progress.update(fetch_task, description=f"[cyan]📥 已获取: {total_fetched}个作品")

                except Exception as e:
                    self.console.print(f"[red]❌ 获取作品列表出错: {str(e)}[/]")
                    break

        if filtered_count > 0:
            self.console.print(f"[yellow]⚠️  已过滤 {filtered_count} 个不在时间范围内的作品[/]")

        return awemeList

    def getUserAllMixInfo(self, sec_uid, count=35, number=0):
        print('[  提示  ]:正在请求的用户 id = %s\r\n' % sec_uid)
        if sec_uid is None:
            return None
        if number <= 0:
            numflag = False
        else:
            numflag = True

        cursor = 0
        mixIdNameDict = {}

        print("[  提示  ]:正在获取主页下所有合集 id 数据请稍后...\r")
        print("[  提示  ]:会进行多次请求，等待时间较长...\r\n")
        times = 0
        while True:
            times = times + 1
            print("[  提示  ]:正在对 [合集列表] 进行第 " + str(times) + " 次请求...\r")

            start = time.time()  # 开始时间
            while True:
                # 接口不稳定, 有时服务器不返回数据, 需要重新获取
                try:
                    url = self.urls.USER_MIX_LIST + utils.getXbogus(
                        f'sec_user_id={sec_uid}&count={count}&cursor={cursor}&device_platform=webapp&aid=6383')

                    res = requests.get(url=url, headers=douyin_headers)
                    datadict = json.loads(res.text)
                    print('[  提示  ]:本次请求返回 ' + str(len(datadict["mix_infos"])) + ' 条数据\r')

                    if datadict is not None and datadict["status_code"] == 0:
                        break
                except Exception as e:
                    end = time.time()  # 结束时间
                    if end - start > self.timeout:
                        print("[  提示  ]:重复请求该接口" + str(self.timeout) + "s, 仍然未获取到数据")
                        return mixIdNameDict


            for mix in datadict["mix_infos"]:
                mixIdNameDict[mix["mix_id"]] = mix["mix_name"]
                if numflag:
                    number -= 1
                    if number == 0:
                        break
            if numflag and number == 0:
                print("\r\n[  提示  ]:[合集列表] 下指定数量合集数据获取完成...\r\n")
                break

            # 更新 max_cursor
            cursor = datadict["cursor"]

            # 退出条件
            if datadict["has_more"] == 0 or datadict["has_more"] == False:
                print("[  提示  ]:[合集列表] 下所有合集 id 数据获取完成...\r\n")
                break
            else:
                print("\r\n[  提示  ]:[合集列表] 第 " + str(times) + " 次请求成功...\r\n")

        return mixIdNameDict

    def getMusicInfo(self, music_id: str, count=35, number=0, increase=False):
        print('[  提示  ]:正在请求的音乐集合 id = %s\r\n' % music_id)
        if music_id is None:
            return None
        if number <= 0:
            numflag = False
        else:
            numflag = True

        cursor = 0
        awemeList = []
        increaseflag = False
        numberis0 = False

        print("[  提示  ]:正在获取音乐集合下的所有作品数据请稍后...\r")
        print("[  提示  ]:会进行多次请求，等待时间较长...\r\n")
        times = 0
        while True:
            times = times + 1
            print("[  提示  ]:正在对 [音乐集合] 进行第 " + str(times) + " 次请求...\r")

            start = time.time()  # 开始时间
            while True:
                # 接口不稳定, 有时服务器不返回数据, 需要重新获取
                try:
                    url = self.urls.MUSIC + utils.getXbogus(
                        f'music_id={music_id}&cursor={cursor}&count={count}&device_platform=webapp&aid=6383')

                    res = requests.get(url=url, headers=douyin_headers)
                    datadict = json.loads(res.text)
                    print('[  提示  ]:本次请求返回 ' + str(len(datadict["aweme_list"])) + ' 条数据\r')

                    if datadict is not None and datadict["status_code"] == 0:
                        break
                except Exception as e:
                    end = time.time()  # 结束时间
                    if end - start > self.timeout:
                        print("[  提示  ]:重复请求该接口" + str(self.timeout) + "s, 仍然未获取到数据")
                        return awemeList


            for aweme in datadict["aweme_list"]:
                if self.database:
                    # 退出条件
                    if increase is False and numflag and numberis0:
                        break
                    if increase and numflag and numberis0 and increaseflag:
                        break
                    # 增量更新, 找到非置顶的最新的作品发布时间
                    if self.db.get_music(music_id=music_id, aweme_id=aweme['aweme_id']) is not None:
                        if increase and aweme['is_top'] == 0:
                            increaseflag = True
                    else:
                        self.db.insert_music(music_id=music_id, aweme_id=aweme['aweme_id'], data=aweme)

                    # 退出条件
                    if increase and numflag is False and increaseflag:
                        break
                    if increase and numflag and numberis0 and increaseflag:
                        break
                else:
                    if numflag and numberis0:
                        break

                if numflag:
                    number -= 1
                    if number == 0:
                        numberis0 = True

                # 清空self.awemeDict
                self.result.clearDict(self.result.awemeDict)

                # 默认为视频
                awemeType = 0
                try:
                    if aweme["images"] is not None:
                        awemeType = 1
                except Exception as e:
                    print("[  警告  ]:接口中未找到 images\r")

                # 转换成我们自己的格式
                self.result.dataConvert(awemeType, self.result.awemeDict, aweme)

                if self.result.awemeDict is not None and self.result.awemeDict != {}:
                    awemeList.append(copy.deepcopy(self.result.awemeDict))

            if self.database:
                if increase and numflag is False and increaseflag:
                    print("\r\n[  提示  ]: [音乐集合] 下作品增量更新数据获取完成...\r\n")
                    break
                elif increase is False and numflag and numberis0:
                    print("\r\n[  提示  ]: [音乐集合] 下指定数量作品数据获取完成...\r\n")
                    break
                elif increase and numflag and numberis0 and increaseflag:
                    print("\r\n[  提示  ]: [音乐集合] 下指定数量作品数据获取完成, 增量更新数据获取完成...\r\n")
                    break
            else:
                if numflag and numberis0:
                    print("\r\n[  提示  ]: [音乐集合] 下指定数量作品数据获取完成...\r\n")
                    break

            # 更新 cursor
            cursor = datadict["cursor"]

            # 退出条件
            if datadict["has_more"] == 0 or datadict["has_more"] == False:
                print("\r\n[  提示  ]:[音乐集合] 下所有作品数据获取完成...\r\n")
                break
            else:
                print("\r\n[  提示  ]:[音乐集合] 第 " + str(times) + " 次请求成功...\r\n")

        return awemeList

    def getUserDetailInfo(self, sec_uid):
        if sec_uid is None:
            return None

        datadict = {}
        start = time.time()  # 开始时间
        while True:
            # 接口不稳定, 有时服务器不返回数据, 需要重新获取
            try:
                url = self.urls.USER_DETAIL + utils.getXbogus(
                        f'sec_user_id={sec_uid}&device_platform=webapp&aid=6383')

                res = requests.get(url=url, headers=douyin_headers)
                datadict = json.loads(res.text)

                if datadict is not None and datadict["status_code"] == 0:
                    return datadict
            except Exception as e:
                end = time.time()  # 结束时间
                if end - start > self.timeout:
                    print("[  提示  ]:重复请求该接口" + str(self.timeout) + "s, 仍然未获取到数据")
                    return datadict


if __name__ == "__main__":
    pass

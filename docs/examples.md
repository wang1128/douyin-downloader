# 使用示例

本文档提供了抖音下载器的详细使用示例，帮助你更好地使用工具。

## 1. 配置文件方式

### 基础配置
创建 `config.yml` 文件：
```yaml
# 下载链接
link:
  - "https://v.douyin.com/xxxxx/"  # 作品链接
  - "https://www.douyin.com/user/xxxxx"  # 用户主页

# 保存路径
path: "./downloads"

# 下载选项
music: true      # 下载音乐
cover: true      # 下载封面
avatar: true     # 下载头像
json: true       # 保存JSON数据
```

运行命令：
```bash
python DouYinCommand.py
```

### 时间范围过滤
```yaml
# 仅下载指定时间范围内的作品
start_time: "2023-01-01"  # 开始时间
end_time: "2023-12-31"    # 结束时间
# 或使用 "now" 表示当前时间
end_time: "now"
```

### 增量更新
```yaml
increase:
  post: true    # 增量更新发布作品
  like: false   # 不增量更新点赞作品
  mix: true     # 增量更新合集
```

### 数量限制
```yaml
number:
  post: 10      # 只下载最新的10个发布作品
  like: 5       # 只下载最新的5个点赞作品
  mix: 3        # 只下载最新的3个合集作品
```

## 2. 命令行方式

### 下载单个视频
```bash
python DouYinCommand.py -C True -l "https://v.douyin.com/xxxxx/"
```

### 下载用户主页作品
```bash
# 下载发布作品
python DouYinCommand.py -C True -l "https://www.douyin.com/user/xxxxx" -M post

# 下载点赞作品
python DouYinCommand.py -C True -l "https://www.douyin.com/user/xxxxx" -M like

# 同时下载发布和点赞作品
python DouYinCommand.py -C True -l "https://www.douyin.com/user/xxxxx" -M post -M like
```

### 下载合集
```bash
# 下载单个合集
python DouYinCommand.py -C True -l "https://www.douyin.com/collection/xxxxx"

# 下载用户所有合集
python DouYinCommand.py -C True -l "https://www.douyin.com/user/xxxxx" -M mix
```

### 自定义保存选项
```bash
# 不下载音乐和封面
python DouYinCommand.py -C True -l "链接" -m False -c False

# 自定义保存路径
python DouYinCommand.py -C True -l "链接" -p "./my_downloads"
```

### 批量下载
```bash
# 下载多个链接
python DouYinCommand.py -C True -l "链接1" -l "链接2" -l "链接3"

# 使用多线程
python DouYinCommand.py -C True -l "链接" -t 10
```

## 3. 高级用法

### Cookie 设置
如果遇到访问限制，可以设置 Cookie：

配置文件方式：
```yaml
cookies:
  msToken: "xxx"
  ttwid: "xxx"
  odin_tt: "xxx"
```

命令行方式：
```bash
python DouYinCommand.py -C True -l "链接" --cookie "msToken=xxx; ttwid=xxx;"
```

### 数据库支持
启用数据库以支持增量更新：
```yaml
database: true
```

### 文件夹风格
控制文件保存结构：
```yaml
folderstyle: true  # 每个作品创建独立文件夹
```

## 4. 常见问题

1. **下载失败**
   - 检查网络连接
   - 更新 Cookie
   - 减少并发线程数

2. **找不到链接**
   - 确保链接格式正确
   - 使用最新的分享链接

3. **增量更新不工作**
   - 确保启用了数据库
   - 检查数据库权限

## 5. 最佳实践

1. 使用配置文件管理复杂的下载任务
2. 适当设置线程数（建议 5-10）
3. 定期更新 Cookie
4. 使用时间范围过滤避免下载太多内容
5. 启用数据库支持增量更新

需要更多帮助，请提交 Issue。

## 错误处理示例

### 1. 网络错误处理
```python
try:
    downloader.download_with_resume(url, filepath, "视频下载")
except requests.exceptions.ConnectionError:
    logger.error("网络连接失败")
except requests.exceptions.Timeout:
    logger.error("下载超时")
```

### 2. 文件系统错误处理
```python
try:
    with open(filepath, 'wb') as f:
        # 下载代码...
except PermissionError:
    logger.error("没有写入权限")
except OSError as e:
    logger.error(f"文件系统错误: {e}") 
# -*- coding: utf-8 -*-
"""
txt2pdf_converter_win_unicode_fixed.py - Unicode修复终极版
"""
import logging
import os
import re
import sys
import tempfile
import winreg
from fpdf import FPDF
from fontTools.ttLib import TTCollection, TTFont
from PIL import Image

# 全局配置
DEFAULT_FONT_SIZE = 12
MAX_PAGE_WIDTH = 210
MAX_PAGE_HEIGHT = 297
VIDEO_EXT = ('.mp4', '.avi', '.mov')
LOG_FILE = "pdf_conversion.log"


def get_system_fonts_dir():
    """获取系统字体目录"""
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows NT\CurrentVersion\Fonts") as key:
            return os.path.join(os.environ['SYSTEMROOT'], 'Fonts')
    except Exception:
        return "C:\\Windows\\Fonts"


def setup_logging():
    """配置日志系统"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('fontTools').setLevel(logging.WARNING)


class UnicodePDF(FPDF):
    def __init__(self):
        super().__init__()
        self.available_fonts = []
        self.current_font = ""
        self._init_pdf()

    def _init_pdf(self):
        """初始化PDF文档"""
        self.add_page()
        self.set_auto_page_break(True, margin=15)
        self.set_margins(20, 25, 20)
        self._load_unicode_fonts()

    def _load_unicode_fonts(self):
        """加载支持Unicode的字体"""
        font_dir = get_system_fonts_dir()
        font_priority = [
            ('SimSun', 'simsun.ttc'),  # 宋体
            ('MicrosoftYaHei', 'msyh.ttc'),  # 微软雅黑
            ('ArialUnicode', 'ARIALUNI.TTF')  # Arial Unicode
        ]

        for name, file in font_priority:
            path = os.path.join(font_dir, file)
            if os.path.exists(path):
                try:
                    self._add_font_safely(name, path)
                except Exception as e:
                    logging.error(f"字体加载失败 {name}: {str(e)}")

        if not self.available_fonts:
            self._add_fallback_font()

        self.current_font = self.available_fonts[0]
        self.set_font(self.current_font, size=DEFAULT_FONT_SIZE)

    def _add_font_safely(self, name, path):
        """安全添加字体"""
        if path.endswith('.ttc'):
            temp_path = self._extract_ttc_font(path, name)
            self.add_font(name, "", temp_path, uni=True)
        else:
            self.add_font(name, "", path, uni=True)
        self.available_fonts.append(name)
        logging.debug(f"成功加载字体: {name}")

    def _extract_ttc_font(self, ttc_path, name):
        """提取TTC字体中的第一个字体"""
        collection = TTCollection(ttc_path)
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, f"{name}.ttf")
        collection.fonts[0].save(temp_path)
        return temp_path

    def _add_fallback_font(self):
        """添加备用字体"""
        try:
            self.add_font('Arial', "", 'arial', uni=True)
            self.available_fonts.append('Arial')
        except RuntimeError:
            self.add_font('Helvetica', "", uni=True)
            self.available_fonts.append('Helvetica')

    def safe_add_text(self, text):
        """安全文本添加方法"""
        try:
            self.multi_cell(0, 10, text)
        except Exception as e:
            logging.warning(f"字符编码问题: {str(e)}")
            cleaned_text = self._sanitize_text(text)
            self.multi_cell(0, 10, cleaned_text)

    def _sanitize_text(self, text):
        """清理无效字符"""
        return ''.join([c if self._is_printable(c) else '�' for c in text])

    def _is_printable(self, char):
        """检查字符是否可打印"""
        try:
            return self.get_string_width(char) >= 0
        except:
            return False

    def add_media_content(self, folder_path):
        """处理多媒体内容"""
        # 处理封面图片
        covers = sorted(
            [f for f in os.listdir(folder_path) if re.match(r'cover_\d{3}\.(jpe?g|png)', f, re.I)],
            key=lambda x: int(re.search(r'\d+', x).group())
        )
        for cover in covers:
            self._add_image_page(os.path.join(folder_path, cover))

        # 处理音频文稿
        audios = sorted(
            [f for f in os.listdir(folder_path) if re.match(r'audio_\d{3}\.txt', f, re.I)],
            key=lambda x: int(re.search(r'\d+', x).group())
        )
        for idx, audio in enumerate(audios, 1):
            self._add_audio_section(os.path.join(folder_path, audio), idx)

    def _add_image_page(self, img_path):
        """添加图片页"""
        self.add_page()
        try:
            with Image.open(img_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                width_ratio = (MAX_PAGE_WIDTH - 40) / img.width
                height_ratio = (MAX_PAGE_HEIGHT - 40) / img.height
                scale = min(width_ratio, height_ratio)

                x = (MAX_PAGE_WIDTH - img.width * scale) / 2
                y = (MAX_PAGE_HEIGHT - img.height * scale) / 2

                self.image(img_path, x=x, y=y, w=img.width * scale)
        except Exception as e:
            logging.error(f"图片处理失败: {img_path}\n{str(e)}")
            raise

    def _add_audio_section(self, txt_path, index):
        """添加音频章节"""
        self.add_page()
        try:
            # 标题部分
            self.set_font(self.current_font, 'B', 16)
            self.cell(0, 10, f"音频文稿 {index:02d}", ln=True)
            self.ln(10)

            # 内容部分
            self.set_font(self.current_font, size=12)
            text_content = self._read_text_file(txt_path)
            self.safe_add_text(text_content)
        except Exception as e:
            logging.error(f"音频处理失败: {txt_path}\n{str(e)}")
            raise

    def _read_text_file(self, path):
        """安全读取文本文件"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'big5']
        for encoding in encodings:
            try:
                with open(path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        raise UnicodeDecodeError(f"无法解码文件: {path}")


def process_folder(folder_path, output_dir, root_folder):
    """处理视频文件夹"""
    try:
        # 输入验证
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"路径不存在: {folder_path}")

        # 生成输出文件名
        rel_path = os.path.relpath(folder_path, root_folder)
        safe_name = re.sub(r'[\\/*?:"<>|]', "_", rel_path)[:100]
        output_name = f"DY视频_{safe_name}.pdf"
        output_path = os.path.join(output_dir, output_name)

        if os.path.exists(output_path):
            logging.info(f"跳过已存在文件: {output_name}")
            return True

        # 创建PDF
        pdf = UnicodePDF()
        pdf.add_media_content(folder_path)

        # 添加详情页
        detail_file = os.path.join(folder_path, 'detail.txt')
        if os.path.exists(detail_file):
            pdf.add_page()
            pdf.set_font(pdf.current_font, 'B', 18)
            pdf.cell(0, 10, "视频详情", ln=True)
            pdf.ln(15)

            detail_content = pdf._read_text_file(detail_file)
            pdf.safe_add_text(detail_content)

        pdf.output(output_path)
        logging.info(f"成功生成: {output_path}")
        return True

    except Exception as e:
        logging.error(f"处理失败: {folder_path}\n{str(e)}")
        return False


def main():
    setup_logging()

    # 配置路径
    root_folder = r"E:\Douyin_Downloaded\user_耶梦加德新书上架橱窗_MS4wLjABAAAA7IklRpIazPeSkxSCaM-9mtUnuPsy1evuu4ogf3m58xI\post\2023-12-12 20.01.22_你的简历里有多少含金量你认为的核心竞争力"
    output_dir = os.path.join(root_folder, "PDF输出")
    os.makedirs(output_dir, exist_ok=True)

    success_count = 0
    error_count = 0

    for foldername, _, filenames in os.walk(root_folder):
        if any(f.lower().endswith(VIDEO_EXT) for f in filenames):
            try:
                if process_folder(foldername, output_dir, root_folder):
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                error_count += 1
                logging.error(f"致命错误: {foldername}\n{str(e)}")

    # 生成报告
    logging.info("\n" + "=" * 50)
    logging.info(f"处理完成! 成功: {success_count} 失败: {error_count}")
    logging.info(f"输出目录: {output_dir}")
    logging.info("=" * 50)


if __name__ == "__main__":
    if sys.platform != 'win32':
        print("仅支持Windows系统")
        sys.exit(1)

    try:
        main()
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(0)
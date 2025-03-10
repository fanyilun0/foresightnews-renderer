import os
import re
import glob
from datetime import datetime

def update_vue_import_path():
    # 查找最新的数据文件
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    data_files = glob.glob(os.path.join(data_dir, "foresight_data_*.json"))

    if not data_files:
        print("No data files found!")
        return False

    # 获取最新的数据文件名
    latest_file = max(data_files, key=os.path.getmtime)
    latest_filename = os.path.basename(latest_file)
    print(f"Latest data file: {latest_filename}")

    # 读取 index.vue 文件
    vue_file_path = os.path.join(os.path.dirname(__file__), "pages", "index.vue")

    with open(vue_file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # 使用正则表达式替换导入路径
    updated_content = re.sub(
        r'import foresightData from \'\.\.\/data\/foresight_data_\d+\.json\'',
        f"import foresightData from '../data/{latest_filename}'",
        content
    )

    # 检查是否有变更
    if content == updated_content:
        print("No changes needed in import path.")
        return False

    # 写回文件
    with open(vue_file_path, 'w', encoding='utf-8') as file:
        file.write(updated_content)

    print(f"Updated import path to: '../data/{latest_filename}'")
    return True

if __name__ == "__main__":
    update_vue_import_path()

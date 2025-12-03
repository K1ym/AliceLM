#!/bin/bash

# 帮助用户在Mac系统（特别是Apple Silicon芯片）上创建虚拟环境并运行项目

# 获取脚本所在目录的绝对路径
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 设置脚本失败时立即退出
set -e

# 检查是否安装了Homebrew
echo "检查Homebrew安装情况..."
if ! command -v brew &> /dev/null
then
    echo "未安装Homebrew，建议先安装Homebrew以获得更好的体验。"
    echo "可以通过以下命令安装Homebrew："
    echo "/bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    echo "安装完成后，请确保运行 'brew install ffmpeg' 安装FFmpeg。"
    echo "
继续不使用Homebrew? (y/n)"
    read -r continue_without_brew
    if [ "$continue_without_brew" != "y" ]
    then
        echo "请安装Homebrew后再运行此脚本。"
        exit 1
    fi
fi

# 检查是否安装了FFmpeg
echo "检查FFmpeg安装情况..."
if ! command -v ffmpeg &> /dev/null
then
    echo "未安装FFmpeg，建议安装FFmpeg以正常处理音频。"
    echo "可以通过Homebrew安装：brew install ffmpeg"
    echo "
继续不使用FFmpeg? (y/n)"
    read -r continue_without_ffmpeg
    if [ "$continue_without_ffmpeg" != "y" ]
    then
        echo "请安装FFmpeg后再运行此脚本。"
        exit 1
    fi
fi

# 切换到脚本所在目录
echo "切换到项目目录: $script_dir"
cd "$script_dir"

# 创建Python虚拟环境
env_name="bili2text-venv"
echo "创建虚拟环境 $env_name..."

# 检查是否安装了Python 3.11
if ! command -v python3.11 &> /dev/null
then
    echo "未检测到Python 3.11，尝试安装..."
    # 检查是否有Homebrew
    if command -v brew &> /dev/null
    then
        echo "通过Homebrew安装Python 3.11..."
        brew install python@3.11
        if ! command -v python3.11 &> /dev/null
        then
            echo "错误：Python 3.11安装失败。请手动安装后重试。"
            echo "可以通过以下命令安装：brew install python@3.11"
            exit 1
        fi
    else
        echo "错误：未检测到Python 3.11，且未安装Homebrew。"
        echo "请先安装Homebrew，然后运行'brew install python@3.11'安装Python 3.11。"
        exit 1
    fi
fi

if [ ! -d "$env_name" ]
then
    python3.11 -m venv "$env_name"
    echo "虚拟环境创建成功！"
else
    echo "虚拟环境已存在，检查Python版本..."
    # 检查虚拟环境的Python版本是否为3.11
    venv_python_version=$("$env_name/bin/python" --version 2>&1)
    if [[ $venv_python_version != *"Python 3.11"* ]]; then
        echo "警告：现有虚拟环境不是Python 3.11版本 ($venv_python_version)"
        echo "建议删除现有虚拟环境重新创建，以确保numba依赖能够正确安装。"
        echo "是否删除现有虚拟环境并重新创建? (y/n)"
        read -r recreate_venv
        if [ "$recreate_venv" = "y" ]
        then
            rm -rf "$env_name"
            python3.11 -m venv "$env_name"
            echo "虚拟环境重新创建成功！"
        fi
    fi
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source "$env_name/bin/activate"

# 升级pip
echo "升级pip..."
pip install --upgrade pip

# 安装项目依赖（使用Mac专用配置）
echo "安装项目依赖（使用Mac专用配置）..."
if [ -f "$script_dir/requirements-mac.txt" ]
then
    pip install -r "$script_dir/requirements-mac.txt"
else
    echo "requirements-mac.txt文件不存在，使用默认requirements.txt..."
    if [ -f "$script_dir/requirements.txt" ]
    then
        pip install -r "$script_dir/requirements.txt"
    else
        echo "错误：找不到requirements-mac.txt和requirements.txt文件！"
        echo "请确保这两个文件中至少有一个存在于项目目录中。"
        exit 1
    fi
fi

# 检查main.py是否存在
echo "检查项目启动文件..."
if [ -f "$script_dir/main.py" ]
then
    echo "正在启动项目..."
    python "$script_dir/main.py"
elif [ -f "$script_dir/window.py" ]
then
    echo "正在启动项目..."
    python "$script_dir/window.py"
else
    echo "未找到启动文件（main.py或window.py），请手动启动项目。"
    echo "当前已激活虚拟环境，您可以运行 'python 文件名.py' 来启动项目。"
fi

echo "项目运行结束。要退出虚拟环境，请输入 'deactivate'。"
#!/bin/bash

# 这个脚本用于在Mac系统上创建一个与bili2text项目兼容的Python虚拟环境
# 主要解决Python 3.13与项目依赖的兼容性问题

# 获取脚本所在目录
sCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$sCRIPT_DIR"

# 检查Homebrew是否安装
if ! command -v brew &> /dev/null; then
    echo "错误: Homebrew未安装。请先安装Homebrew:"
    echo "/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)""
    exit 1
fi

# 检查是否安装了Python 3.11
if ! command -v python3.11 &> /dev/null; then
    echo "Python 3.11未安装，正在通过Homebrew安装..."
    brew install python@3.11
    if ! command -v python3.11 &> /dev/null; then
        echo "错误: Python 3.11安装失败。请手动安装后重试。"
        exit 1
    fi
else
    echo "已检测到Python 3.11"
fi

# 检查是否安装了FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "FFmpeg未安装，正在通过Homebrew安装..."
    brew install ffmpeg
    if ! command -v ffmpeg &> /dev/null; then
        echo "错误: FFmpeg安装失败。请手动安装后重试。"
        exit 1
    fi
else
    echo "已检测到FFmpeg"
fi

# 创建新的虚拟环境
env_name="bili2text-venv-py311"
echo "正在创建Python 3.11虚拟环境: $env_name"
rm -rf "$env_name"  # 移除已存在的虚拟环境
python3.11 -m venv "$env_name"

# 激活虚拟环境
source "$env_name/bin/activate"

# 升级pip
echo "正在升级pip..."
pip install --upgrade pip

# 安装项目依赖
requirements_file="requirements-mac.txt"
if [ -f "$requirements_file" ]; then
    echo "正在安装项目依赖 (使用$requirements_file)..."
    pip install -r "$requirements_file"
else
    echo "错误: $requirements_file 文件不存在！"
    deactivate
    exit 1
fi

# 验证安装是否成功
if [ $? -eq 0 ]; then
    echo "\n\n✅ 安装成功！"
    echo "\n使用以下命令运行项目:"
    echo "1. 激活虚拟环境: source $env_name/bin/activate"
    echo "2. 启动GUI界面: python window.py"
    echo "   或命令行方式: python main.py"
    echo "\n也可以直接运行: ./run-in-compatible-venv.sh"
else
    echo "\n❌ 安装失败，请查看错误信息。"
    deactivate
    exit 1
fi

# 创建运行脚本
cat > run-in-compatible-venv.sh << 'EOL'
#!/bin/bash

sCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$sCRIPT_DIR"

echo "正在激活Python 3.11虚拟环境..."
source bili2text-venv-py311/bin/activate

# 运行GUI界面
echo "正在启动bili2text..."
python window.py

# 脚本结束后自动退出虚拟环境
deactivate
EOL

# 给运行脚本添加执行权限
chmod +x run-in-compatible-venv.sh

echo "已创建快捷运行脚本: run-in-compatible-venv.sh"

# 退出虚拟环境
deactivate
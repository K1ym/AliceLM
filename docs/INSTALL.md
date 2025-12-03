# Mac系统（Apple Silicon）安装指南

## 特别说明

我们已经优化了Mac系统的安装流程，现在使用**Python 3.11版本**来确保所有依赖项（包括numba）能够正确安装。

numba库已经重新添加到`requirements-mac.txt`文件中，并使用与Python 3.11兼容的版本(0.59.1)。

我们还调整了numpy版本为1.26.4，这是因为numba 0.59.1需要numpy<1.27且>=1.22，而原项目使用的numpy 2.0.0与其不兼容。

## 安装步骤

### 方法1：使用run-mac.sh脚本（推荐）

1. 打开终端，进入项目目录：
   ```
   cd /Users/kyo/Downloads/bili2text-main
   ```

2. 运行安装脚本：
   ```
   ./run-mac.sh
   ```

   脚本会自动：
   - 检查Homebrew和FFmpeg的安装情况
   - 检查并安装Python 3.11（如需要）
   - 创建基于Python 3.11的虚拟环境
   - 安装Mac专用的依赖（包括与Python 3.11兼容的numba）
   - 启动项目

### 方法2：手动安装

如果您想手动控制安装过程，可以按照以下步骤操作：

1. 确保已安装Homebrew和FFmpeg：
   ```
   # 安装Homebrew（如未安装）
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   
   # 安装FFmpeg
   brew install ffmpeg
   ```

2. 安装Python 3.11：
   ```
   brew install python@3.11
   ```

3. 创建并激活虚拟环境（使用Python 3.11）：
   ```
   python3.11 -m venv bili2text-venv
   source bili2text-venv/bin/activate
   ```

4. 升级pip：
   ```
   pip install --upgrade pip
   ```

5. 安装项目依赖：
   ```
   pip install -r requirements-mac.txt
   ```

6. 运行项目：
   ```
   python window.py  # 启动GUI界面
   # 或
   python main.py    # 命令行方式
   ```

## 常见问题及解决方案

### 1. FFmpeg未安装

如果遇到FFmpeg相关错误，请使用Homebrew安装：
```
brew install ffmpeg
```

### 2. PyTorch在Apple Silicon上性能不佳

如果您发现Whisper模型运行缓慢，可以尝试安装专为Apple Silicon优化的PyTorch版本：
```
# 卸载当前PyTorch
pip uninstall torch

# 安装专为Apple Silicon优化的版本
pip install torch torchvision torchaudio
```

### 3. 虚拟环境创建失败

如果虚拟环境创建失败，可以尝试使用不同的Python版本：
```
# 查看已安装的Python版本
ls -la /usr/bin/python*

# 使用特定版本创建虚拟环境
python3.12 -m venv bili2text-venv
```

### 4. 项目运行时出错

如果项目运行时出现错误，请确保：
- 所有依赖都已正确安装
- FFmpeg可在命令行中使用
- 您有足够的磁盘空间来存储下载的视频和音频文件

## 验证安装

安装完成后，您可以运行以下命令验证主要依赖是否正确安装：
```
# 验证FFmpeg
ffmpeg -version

# 验证Python依赖
pip list | grep -E "torch|openai-whisper|moviepy|pydub|ttkbootstrap"
```

## 提示

- 如果您遇到其他兼容性问题，可以考虑使用Python 3.12版本，因为它与更多库兼容
- 对于大型视频文件，建议确保您的设备有足够的内存（至少8GB）
- 首次加载Whisper模型可能需要一些时间，请耐心等待

如有其他问题，请参考项目的README-MAC.md文件或在GitHub上提交issue。
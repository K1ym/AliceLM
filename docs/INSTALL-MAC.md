# Bili2Text - Mac系统运行指南

本指南提供了如何在Mac系统（特别是Apple Silicon芯片的Mac）上运行Bili2Text项目的详细步骤。

## 系统要求

- MacOS 12.0+（推荐）
- Python 3.8+ 
- Homebrew（用于安装依赖）
- 至少8GB RAM（推荐16GB以上）
- 足够的磁盘空间（用于存储视频和音频文件）

## 安装步骤

### 1. 安装Homebrew

如果您尚未安装Homebrew，请打开Terminal（终端）并执行以下命令：

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

按照提示完成安装。

### 2. 安装FFmpeg

Bili2Text需要FFmpeg来处理视频和音频文件。使用Homebrew安装FFmpeg：

```bash
brew install ffmpeg
```

### 3. 克隆项目仓库

```bash
git clone https://github.com/lanbinleo/bili2text.git
cd bili2text
```

### 4. 安装Python依赖

#### 4.1 安装适配Apple Silicon的PyTorch

```bash
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

#### 4.2 安装项目依赖

```bash
pip3 install -r requirements.txt
```

## 运行程序

### 使用GUI界面（推荐）

```bash
python3 window.py
```

### 使用命令行界面

```bash
python3 main.py
```

然后按照提示输入BV号。

## 常见问题与解决方案

### 1. 程序启动时出现"无法设置图标"错误

这是正常现象，Mac系统与Windows的图标格式不兼容，但不会影响程序功能。

### 2. 视频下载失败

- 确保您的网络连接正常
- 检查BV号是否正确
- 尝试更新you-get：`pip3 install --upgrade you-get`

### 3. 语音识别速度慢

- 在Apple Silicon芯片上，首次加载模型可能需要较长时间
- 对于长视频，可以选择更小的模型（如"tiny"或"small"）以提高速度
- 确保您的Mac有足够的可用内存

### 4. 音频提取或分割失败

- 确保FFmpeg已正确安装：`which ffmpeg` 应该显示安装路径
- 尝试更新FFmpeg：`brew update && brew upgrade ffmpeg`

### 5. 程序崩溃或无响应

- 检查Python版本是否符合要求
- 尝试重新安装依赖：`pip3 install --upgrade -r requirements.txt`
- 对于内存不足的情况，可以尝试关闭其他应用程序

## 优化建议

### 对于Apple Silicon芯片用户

1. **选择合适的模型大小**
   - 小型模型（tiny、small）：速度快，适合一般用途
   - 中型模型（medium）：平衡的速度和准确性
   - 大型模型（large）：最高准确性，但速度较慢

2. **关闭不必要的应用**
   运行Whisper模型时会消耗较多内存，关闭其他应用程序可以提高性能。

3. **定期更新依赖**
   ```bash
   pip3 install --upgrade torch whisper moviepy pydub
   brew update && brew upgrade ffmpeg
   ```

## 联系支持

如果您在Mac上运行项目时遇到其他问题，请在GitHub仓库提交Issue：

https://github.com/lanbinleo/bili2text/issues

## 许可证

本项目根据MIT许可证发布。
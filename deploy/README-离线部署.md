# CSV Web 离线部署

这个项目运行时不依赖外网。
静态页面、样式和脚本都在本地，离线环境真正需要解决的只有 Python 和依赖安装。

## 1. 前提

- 目标服务器建议使用 Windows x64
- Python 版本建议和开发机保持一致：`Python 3.11.x`
- 如果服务器没有 Python，需要先把 Python 安装包复制过去离线安装

### 如果服务器没有 Python

最简单的办法是：

1. 在有网电脑下载 `Python 3.11.x Windows x64` 安装包
2. 拷贝到无网服务器
3. 离线安装时勾选 `Add python.exe to PATH`
4. 安装完成后确认：

```powershell
python --version
```

如果你不想装到系统里，也可以把 Python 的便携版一起放进部署包，但那样需要另外改启动脚本。

## 2. 在有网电脑上准备离线包

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\build_offline_bundle.ps1 -PythonInstaller "D:\安装\python-3.11.9-amd64.exe"
```

执行后会生成：

- `offline_bundle\`
- `offline_bundle.zip`

里面已经包含：

- `app.py`
- `static\`
- `工艺规程文件\`
- `requirements.txt`
- `packages\` 离线依赖包
- `install_offline.ps1`
- `start_csvweb.ps1`
- `setup_server_offline.ps1`
- `setup_and_run.bat`
- `python-3.11.9-amd64.exe`（如果你传了 `-PythonInstaller`）

## 3. 拷贝到无网服务器

把下面任意一个复制到服务器：

- `offline_bundle.zip`
- 或整个 `offline_bundle\` 文件夹

例如放到：

```text
D:\csvweb-offline
```

## 4. 在无网服务器安装

先进入部署目录：

```powershell
cd D:\csvweb-offline
```

执行离线安装：

```powershell
powershell -ExecutionPolicy Bypass -File .\install_offline.ps1
```

它会：

- 创建 `.venv`
- 从本地 `packages\` 安装依赖

### 更简单的一键方式

如果离线包里已经带了 `python-3.11.9-amd64.exe`，在服务器上直接双击：

```text
setup_and_run.bat
```

它会自动：

- 安装 Python 3.11
- 创建虚拟环境
- 离线安装依赖
- 直接启动服务

## 5. 启动服务

```powershell
powershell -ExecutionPolicy Bypass -File .\start_csvweb.ps1
```

默认监听：

```text
http://0.0.0.0:8765
```

如果只允许本机访问：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_csvweb.ps1 -HostAddress 127.0.0.1 -Port 8765
```

如果局域网其他电脑也要访问，保持 `0.0.0.0`，然后开放服务器防火墙的 `8765` 端口。

## 6. 访问方式

- 服务器本机访问：`http://127.0.0.1:8765`
- 局域网访问：`http://服务器IP:8765`

## 7. 后续更新

如果你后面又改了代码或 CSV：

1. 在有网电脑重新执行 `build_offline_bundle.ps1`
2. 把新的 `offline_bundle.zip` 复制到服务器
3. 覆盖旧目录
4. 重新执行 `install_offline.ps1`
5. 重启服务

## 8. 常见问题

### 依赖安装失败

通常是 Python 主版本不一致。
例如你在开发机用的是 Python 3.11，但服务器装的是 3.9 或 3.12。

### 能启动但别人访问不到

通常是两个原因：

- 启动时用了 `127.0.0.1`
- Windows 防火墙没开放 `8765`

### CSV 中文乱码

当前程序会自动识别常见编码，并优先兼容 `gb18030/gbk`，适合你现在这批文件。

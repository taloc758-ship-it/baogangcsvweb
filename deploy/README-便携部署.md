# CSV Web 便携部署

这个版本的目标是：

- 目标服务器没有外网
- 目标服务器没有 Python
- 你只复制一个文件夹过去就能运行

## 1. 在当前电脑生成便携包

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\build_portable_bundle.ps1
```

执行完成后会生成：

- `portable_bundle\`
- `portable_bundle.zip`

## 2. 复制到目标服务器

把 `portable_bundle\` 整个目录复制到服务器，比如：

```text
D:\csvweb-portable
```

或者直接复制 `portable_bundle.zip`，到服务器后解压。

## 3. 启动

进入目录后，直接运行：

```text
run_portable.bat
```

或者用 PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\run_portable.ps1
```

默认地址：

```text
http://127.0.0.1:8765
```

局域网其他电脑访问：

```text
http://服务器IP:8765
```

## 4. 注意

- 这个便携包直接复制了当前电脑的 Python 运行时
- 目标机器建议也是 Windows x64
- 如果目标机系统太旧，可能还需要微软 VC 运行库

## 5. 修改 CSV

CSV 文件就在便携目录里的：

```text
工艺规程文件\
```

程序会直接修改这里面的文件。

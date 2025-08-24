# **PyUtilScripts**  

`PyUtilScripts` 是一个基于 Python 的通用小工具集合，目标是提供编写通用任务的辅助工具。  

## 📦 安装

### 通过 pip 安装

```bash
pip install pyutilscripts
```

### 从源码安装

```bash
git clone https://github.com/ZeroKwok/PyUtilScripts.git
cd PyUtilScripts
pip install .
```

---

## 📝 使用说明

- **fcopy**
  - 基于清单文件的复制工具
  - 特点
    - 支持 更新、覆盖写、重命名模式
    - 支持 交互模式，精准把控拷贝细节（拷贝前生成行动列表，在用户编辑或确认后，才具体执行行动列表中记录的动作）
    - 支持 过滤模式，忽略某些文件或目录
  - 示例：
    - 按文件清单拷贝指定目录下的文件
      - 更新模式 `fcopy -l /path/to/list.txt -s /path/to/src -t /path/to/dest`
      - 覆盖模式 `fcopy -l /path/to/list.txt -s /path/to/src -t /path/to/dest -m o`
      - 重命名模式 `fcopy -l /path/to/list.txt -s /path/to/src -t /path/to/dest -m r`
    - 通过指定目录下的文件生成文件清单
      - `fcopy -l /path/to/list.txt -s /path/to/src --update-list`
    - 交互模式下拷贝指定目录的文件
      - `fcopy -l /path/to/list.txt -s /path/to/src -t /path/to/dest -i`
  - 概念
    - 文件清单(fcopy.list)决定要拷贝的文件
    - 行动清单决定拷贝行为(交互模式下通过编辑器呈现)

- **prunedirs**
  - 递归删除空目录
  - 示例：
    - `prunedirs /path/to/dir`

- **forward.tcp**
  - TCP 端口转发工具
  - 示例：
    - `forward.tcp -s 0.0.0.0:8081 -d 127.0.0.1:1081`

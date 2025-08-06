# **PyUtilScripts**  

`PyUtilScripts` 是一个基于 Python 的通用小工具集合，目标是提供编写通用任务的辅助工具。  

## **📜 脚本列表**  

| 脚本名称 | 功能描述 | 示例用法 |
|----------|---------|---------|
| [`fcopy.py`](fcopy.py) | 基于清单文件的复制工具 | `fcopy -l list.txt -s src_dir -d dest_dir` |
| [`forward-tcp.py`](forward-tcp.py) | TCP 端口转发工具 | `forward-tcp -s 0.0.0.0:8081 -d 127.0.0.1:1081` |
| [`prunedirs.py`](prunedirs.py) | 递归删除空目录 | `prunedirs /path/to/dir` |

---

## **⚙️ 安装与使用**  

### **1. 克隆仓库**  

```bash
git clone https://github.com/ZeroKwok/PyUtilScripts.git
cd PyUtilScripts
```

### **2. 直接运行（无需安装）**  

所有脚本均可直接执行：  

```bash
python3 script_name.py [args]
```

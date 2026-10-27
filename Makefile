# ReadmeLint Makefile — 跨平台可用（在 PowerShell / bash / sh 下均可用 make）
# ReadmeLint Makefile — works cross-platform.

PY ?= python3
PKG := readmelint

.PHONY: help install dev test lint selfcheck build clean

help:  ## 显示帮助
	@echo "Targets: install | dev | test | lint | selfcheck | build | clean"

install:  ## 安装到当前 Python 环境
	$(PY) -m pip install .

dev:  ## 以可编辑模式安装（含测试依赖）
	$(PY) -m pip install -e .

test:  ## 运行单元测试
	$(PY) -m unittest tests_readmelint.test_readmelint -v

lint:  ## 语法与导入自检
	$(PY) -m py_compile $(PKG)/*.py tests_readmelint/*.py
	$(PY) -c "import $(PKG); print('import ok:', $(PKG).__version__)"

selfcheck:  ## 用 ReadmeLint 检测自身 README
	$(PY) -m $(PKG).cli lint README.md --format text

build:  ## 构建 wheel / sdist
	$(PY) -m pip install build >/dev/null 2>&1 || true
	$(PY) -m build

clean:  ## 清理构建产物
	rm -rf build dist *.egg-info $(PKG)/__pycache__ tests/__pycache__ .pytest_cache
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +

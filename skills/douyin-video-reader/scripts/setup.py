#!/usr/bin/env python3
"""安装本 Skill 的运行时依赖：只装到 .runtime/deps，不使用系统全局环境。

浏览器二进制不下载：直接复用本机 Chrome 的无窗口模式（channel='chrome'）。
"""
import argparse, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dependencies', action='store_true')
    ap.add_argument('--index-url', default='https://pypi.org/simple')
    args = ap.parse_args()
    if not args.dependencies:
        ap.error('Select --dependencies')
    RUNTIME.mkdir(exist_ok=True)
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--only-binary=:all:',
                    '--target', str(RUNTIME / 'deps'), 'playwright',
                    '--index-url', args.index_url, '--disable-pip-version-check'], check=True)
    print('deps ready: playwright（使用本机 Chrome，无窗口模式，不下载浏览器包）', flush=True)


if __name__ == '__main__':
    main()

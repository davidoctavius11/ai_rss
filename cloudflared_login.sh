#!/bin/bash

# 设置API令牌
export CLOUDFLARE_API_TOKEN="UfsHQTxLEjKTLCtbIZmF1bvN3HYYjXD30zhu-IaS"

echo "步骤1: 尝试使用API令牌登录..."
cloudflared tunnel login

echo ""
echo "如果上面的命令失败，请尝试以下手动步骤："
echo "1. 打开浏览器访问：https://dash.cloudflare.com/argotunnel"
echo "2. 登录您的Cloudflare账户"
echo "3. 授权cloudflared访问"
echo "4. 下载证书文件"
echo "5. 将证书文件保存为: /Users/ioumvp/.cloudflared/cert.pem"
echo ""
echo "完成后，运行以下命令检查："
echo "ls -la ~/.cloudflared/cert.pem"
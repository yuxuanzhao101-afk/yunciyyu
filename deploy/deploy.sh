#!/bin/bash
# yunciyyu.top 部署脚本
# 在阿里云服务器上运行

set -e

echo "=========================================="
echo "  yunciyyu.top 部署脚本"
echo "=========================================="

# 配置
APP_DIR="/var/www/yunciyyu"
DOMAIN="yunciyyu.top"

# 1. 安装系统依赖
echo "[1] 安装系统依赖..."
apt update
apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git

# 2. 创建应用目录
echo "[2] 创建应用目录..."
mkdir -p $APP_DIR
mkdir -p /var/log/yunciyyu
mkdir -p $APP_DIR/static/quote_images
mkdir -p $APP_DIR/backups

# 3. 克隆代码（如果是从 Git）
# git clone https://github.com/yourusername/yunciyyu.git $APP_DIR
# 或者手动上传代码

# 4. 创建虚拟环境并安装依赖
echo "[3] 安装 Python 依赖..."
cd $APP_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install flask gunicorn gevent

# 5. 配置 Nginx
echo "[4] 配置 Nginx..."
cp deploy/nginx.conf /etc/nginx/sites-available/yunciyyu
ln -sf /etc/nginx/sites-available/yunciyyu /etc/nginx/sites-enabled/yunciyyu
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# 6. 配置 Systemd 服务
echo "[5] 配置 Systemd 服务..."
cp deploy/yunciyyu.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable yunciyyu

# 7. 申请 SSL 证书
echo "[6] 申请 SSL 证书..."
certbot certonly --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email your@email.com

# 8. 设置权限
echo "[7] 设置权限..."
chown -R www-data:www-data $APP_DIR
chown -R www-data:www-data /var/log/yunciyyu
chmod 600 $APP_DIR/schedule.db  # 数据库文件

# 9. 启动服务
echo "[8] 启动服务..."
systemctl start yunciyyu
systemctl status yunciyyu

echo "=========================================="
echo "  部署完成！"
echo "  访问: https://$DOMAIN"
echo "=========================================="
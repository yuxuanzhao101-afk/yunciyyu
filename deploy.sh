#!/bin/bash

set -e

echo "=========================================="
echo "   yunciyyu.xyz 自动部署脚本"
echo "=========================================="

APP_DIR="/var/www/yunciyyu"
DOMAIN="yunciyyu.xyz"

echo "[1/8] 更新系统..."
apt update && apt upgrade -y

echo "[2/8] 安装依赖..."
apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git

echo "[3/8] 创建项目目录..."
mkdir -p $APP_DIR
cd $APP_DIR

echo "[4/8] 创建Python虚拟环境..."
python3 -m venv venv
source venv/bin/activate

echo "[5/8] 安装Python依赖..."
if [ -f requirements.txt ]; then
    pip install -r requirements.txt gunicorn
else
    pip install flask gunicorn
fi

echo "[6/8] 创建Systemd服务..."
cat > /etc/systemd/system/yunciyyu.service << EOF
[Unit]
Description=yunciyyu Flask App
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 3 --bind unix:yunciyyu.sock -m 007 app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable yunciyyu
systemctl start yunciyyu

echo "[7/8] 配置Nginx..."
cat > /etc/nginx/sites-available/yunciyyu << EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    location / {
        include proxy_params;
        proxy_pass http://unix:$APP_DIR/yunciyyu.sock;
    }

    location /static {
        alias $APP_DIR/static;
        expires 30d;
    }
}
EOF

ln -sf /etc/nginx/sites-available/yunciyyu /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

echo "[8/8] 配置SSL证书..."
echo "请确保域名已解析到本服务器IP，按Enter继续..."
read -r
certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --register-unsafely-without-email || echo "SSL配置失败，请检查域名解析"

echo ""
echo "=========================================="
echo "   部署完成！"
echo "=========================================="
echo ""
echo "访问地址: https://$DOMAIN"
echo ""
echo "常用命令:"
echo "  查看状态: systemctl status yunciyyu"
echo "  重启应用: systemctl restart yunciyyu"
echo "  查看日志: journalctl -u yunciyyu -f"
echo ""

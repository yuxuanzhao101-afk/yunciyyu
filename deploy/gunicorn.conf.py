# yunciyyu.top 生产环境部署配置

import gevent.monkey
gevent.monkey.patch_all()

bind = "127.0.0.1:5000"
workers = 3
worker_class = "gevent"
threads = 1
timeout = 30
keepalive = 2
preload_app = True
daemon = False
pidfile = "/var/run/yunciyyu.pid"
errorlog = "/var/log/yunciyyu/error.log"
accesslog = "/var/log/yunciyyu/access.log"
loglevel = "info"
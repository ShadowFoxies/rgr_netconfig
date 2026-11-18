#!/bin/bash
# Автоматично згенерований скрипт конфігурації вузла: gw-kremenchuk-01
set -e

# === 1. Налаштування мережевих інтерфейсів ===
ip link set dev eth1 mtu 1500
ip addr replace 10.20.0.1/16 dev eth1
ip link set dev eth1 up
ip link set dev eth2 mtu 1400
ip addr replace 172.16.5.1/24 dev eth2
ip link set dev eth2 down
ip link set dev eth0 mtu 1500
ip addr replace 192.168.10.1/24 dev eth0
ip link set dev eth0 up
ip link add link eth0 name eth0.20 type vlan id 20
ip link set dev eth0.20 mtu 1500
ip addr replace 192.168.20.1/24 dev eth0.20
ip link set dev eth0.20 up
ip link add link eth0 name eth0.30 type vlan id 30
ip link set dev eth0.30 mtu 1500
ip addr replace 192.168.30.1/24 dev eth0.30
ip link set dev eth0.30 up

# === 2. Налаштування таблиці статичної маршрутизації ===
ip route replace 10.100.0.0/16 via 192.168.10.254 dev eth0 metric 10
ip route replace 172.31.0.0/16 via 10.20.0.254 dev eth1 metric 20
ip route replace 192.168.200.0/24 via 192.168.20.254 dev eth0.20 metric 50
ip route replace 0.0.0.0/0 via 192.168.10.254 dev eth0 metric 100

echo "Конфігурацію вузла gw-kremenchuk-01 успішно застосовано."

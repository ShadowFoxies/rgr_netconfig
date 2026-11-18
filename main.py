"""
Точка входу та інтерфейс командного рядка (CLI) модуля netconfig.
Підтримує розбір sys.argv, генерацію звітів, JSON/CSV серіалізацію та бенчмаркінг.
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

from netconfig import (
    NetConfigError,
    NetworkInterface,
    RouterConfigurator,
    StaticRoute,
    load_from_json,
    load_text_config,
    save_script,
    save_to_csv,
    save_to_json,
)


def print_usage() -> None:
    """Виводить довідку щодо аргументів командного рядка."""
    print("Використання: python main.py [ОПЦІЇ]")
    print("Опції:")
    print("  --input <шлях>      Шлях до текстового файлу конфігурації (.conf)")
    print("  --from-json <шлях>  Відновити конфігурацію з існуючого JSON-файлу")
    print("  --out-dir <папка>   Директорія для збереження JSON, CSV та .sh (за замовч. data/output)")
    print("  --benchmark         Запустити тестування швидкодії (time.perf_counter)")
    print("  --help              Показати цю довідку")


def print_report(configurator: RouterConfigurator, elapsed_ms: float) -> None:
    """Форматований вивід таблиць інтерфейсів, маршрутів та згенерованого скрипта."""
    sep = "=" * 88
    sub_sep = "-" * 88

    print(sep)
    print(f"{f'ЗВІТ КОНФІГУРУВАННЯ МЕРЕЖЕВОГО ВУЗЛА: {configurator.hostname}':^88}")
    print(sep)
    print(f"Активних і всього інтерфейсів: {len(configurator.interfaces)}")
    print(f"Кількість статичних маршрутів: {len(configurator.routes)}")
    print(f"Сумарна пропускна здатність (UP): {configurator.total_enabled_bandwidth_mbps()} Мбіт/с")

    print(sub_sep)
    print(f"| {'Інтерфейс':<12} | {'IP / Маска':<18} | {'MAC-адреса':<17} | {'MTU':<5} | {'Мбіт/с':<7} | {'Стан':<6} |")
    print(sub_sep)
    for iface in configurator.get_sorted_interfaces():
        state = "UP" if iface.enabled else "DOWN"
        print(
            f"| {iface.name:<12} | {iface.cidr:<18} | {iface.mac_address:<17} | "
            f"{iface.mtu:<5} | {iface.bandwidth_mbps:<7} | {state:<6} |"
        )

    print(sub_sep)
    print(f"| {'Цільова мережа':<18} | {'Шлюз (Gateway)':<16} | {'Інтерфейс':<12} | {'Метрика':<8} | {'Статус':<8} |")
    print(sub_sep)
    for route in configurator.get_sorted_routes():
        state = "ACTIVE" if route.enabled else "OFF"
        print(
            f"| {route.cidr:<18} | {route.gateway:<16} | {route.interface_name:<12} | "
            f"{route.metric:<8} | {state:<8} |"
        )

    print(sep)
    print("ЗГЕНЕРОВАНИЙ BASH-СКРИПТ:")
    print(sub_sep)
    print(configurator.generate_script().rstrip())
    print(sep)
    print(f"Час обробки конфігурації: {elapsed_ms:.4f} мс")


def run_benchmark(out_dir: Path) -> None:
    """Бенчмаркінг швидкодії побудови та генерації скриптів на різних обсягах N."""
    sizes = [100, 500, 1000, 2500, 5000, 10000]
    results: list[dict] = []

    sep = "=" * 78
    sub_sep = "-" * 78
    print(sep)
    print(f"{'БЕНЧМАРКІНГ ШВИДКОДІЇ МОДУЛЯ NETCONFIG (time.perf_counter)':^78}")
    print(sep)
    print(f"| {'N (сутностей)':<14} | {'Побудова (мс)':<16} | {'Скрипт (мс)':<15} | {'Разом (мс)':<15} |")
    print(sub_sep)

    for n in sizes:
        rc = RouterConfigurator(f"bench-{n}")

        t0 = time.perf_counter()
        # Створюємо базові підмережі та маршрути
        iface_count = max(1, n // 10)
        for i in range(iface_count):
            octet2 = (i // 250) % 250
            octet3 = i % 250
            rc.add_interface(
                NetworkInterface(
                    name=f"eth{i}",
                    ip_address=f"10.{octet2}.{octet3}.1",
                    prefix=24,
                    mac_address=f"aa:bb:cc:00:{octet2:02x}:{octet3:02x}",
                )
            )

        route_count = n - iface_count
        for j in range(route_count):
            idx = j % iface_count
            octet2 = (idx // 250) % 250
            octet3 = idx % 250
            dst_o2 = (j // 250) % 250
            dst_o3 = j % 250
            rc.add_route(
                StaticRoute(
                    destination=f"172.{dst_o2}.{dst_o3}.0",
                    prefix=24,
                    gateway=f"10.{octet2}.{octet3}.254",
                    interface_name=f"eth{idx}",
                    metric=(j % 200) + 1,
                )
            )
        t1 = time.perf_counter()

        _ = rc.generate_script()
        t2 = time.perf_counter()

        build_ms = (t1 - t0) * 1000
        gen_ms = (t2 - t1) * 1000
        total_ms = (t2 - t0) * 1000

        print(f"| {n:<14} | {build_ms:<16.3f} | {gen_ms:<15.3f} | {total_ms:<15.3f} |")
        results.append(
            {
                "entities_n": n,
                "build_ms": round(build_ms, 4),
                "script_gen_ms": round(gen_ms, 4),
                "total_ms": round(total_ms, 4),
            }
        )

    print(sep)

    bench_csv = out_dir / "benchmark_results.csv"
    bench_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(bench_csv, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=["entities_n", "build_ms", "script_gen_ms", "total_ms"]
        )
        writer.writeheader()
        writer.writerows(results)
    print(f"Результати бенчмарку збережено у: {bench_csv}")


def parse_cli_args(argv: list[str]) -> dict:
    """Розбирає аргументи командного рядка sys.argv."""
    options = {
        "input_file": None,
        "from_json": None,
        "out_dir": Path("data/output"),
        "benchmark": False,
        "help": False,
    }

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("-h", "--help"):
            options["help"] = True
        elif arg == "--benchmark":
            options["benchmark"] = True
        elif arg == "--input" and i + 1 < len(argv):
            options["input_file"] = Path(argv[i + 1])
            i += 1
        elif arg == "--from-json" and i + 1 < len(argv):
            options["from_json"] = Path(argv[i + 1])
            i += 1
        elif arg == "--out-dir" and i + 1 < len(argv):
            options["out_dir"] = Path(argv[i + 1])
            i += 1
        else:
            raise ValueError(f"Невідомий або неповний аргумент CLI: '{arg}'")
        i += 1

    return options


def main() -> int:
    """Головна функція CLI-утиліти."""
    try:
        opts = parse_cli_args(sys.argv[1:])
    except ValueError as exc:
        print(f"[ПОМИЛКА CLI] {exc}", file=sys.stderr)
        print_usage()
        return 2

    if opts["help"]:
        print_usage()
        return 0

    out_dir: Path = opts["out_dir"]

    if opts["benchmark"]:
        run_benchmark(out_dir)
        return 0

    try:
        t_start = time.perf_counter()

        if opts["from_json"]:
            configurator = load_from_json(opts["from_json"])
        else:
            input_path = opts["input_file"] or Path("data/sample_network.conf")
            configurator = load_text_config(input_path)

        json_path = save_to_json(configurator, out_dir / "config.json")
        csv_path = save_to_csv(configurator, out_dir / "report.csv")
        sh_path = save_script(configurator.generate_script(), out_dir / "apply_routes.sh")

        elapsed_ms = (time.perf_counter() - t_start) * 1000
        print_report(configurator, elapsed_ms)
        print(f"Створені артефакти:\n  - JSON: {json_path}\n  - CSV:  {csv_path}\n  - BASH: {sh_path}")
        return 0

    except NetConfigError as exc:
        print(
            f"\n[АВАРІЙНИЙ СТАН СИСТЕМИ] {exc.__class__.__name__}: {exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
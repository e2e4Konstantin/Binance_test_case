import httpx
from datetime import datetime, timezone, timedelta
import time
import statistics
import math
import asyncio

from binance_limits import base_url, symbol, MINUTE_LIMIT, yellow_ch, reset_ch


async def get_last_hour_high_price() -> tuple[float | None, int | None, int | None]:
    """
    Запрашивает данные о последних двух часах
    :return: Максимальную цену за прошлый час, Время закрытия прошлого часа, Вес запроса
    """
    total_weight, high_price, close_time = None, None, None
    end_point = "/fapi/v1/klines"
    url = f"{base_url}{end_point}"
    param = {'symbol': symbol, 'interval': '1h', 'limit': 2}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=param)
    try:
        total_weight = int(response.headers.get('X-MBX-USED-WEIGHT-1M', 0))
        data = response.json()
        high_price = float(data[0][2])
        close_time = data[0][6] // 1000
        open_time = data[0][0] // 1000
    except ValueError as err:
        data = response.text
        print(data, err)
    return high_price, close_time, total_weight


async def io_get_price() -> tuple[float | None, float | None, int | None]:
    """
    Запрашивает текущую цену.
    :return: Цена, Вес запроса, Время выполнения
    """
    price, weight, elapsed_time = None, None, None

    end_point = "/fapi/v1/ticker/price"
    url = f"{base_url}{end_point}"
    param = {'symbol': symbol}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=param)
    try:
        weight = int(response.headers.get('X-MBX-USED-WEIGHT-1M', None))
        data = response.json()
        price = data.get('price', None)
        price = float(price) if price else None
        elapsed_time = response.elapsed.microseconds
    except ValueError as err:
        data = response.text
        print(data, err)
    return price, weight, elapsed_time


def time_info():
    """
    Информация о текущем времени на сервере и здесь
    """
    response = httpx.get(url="https://fapi.binance.com/fapi/v1/time")
    elapsed_time = response.elapsed.total_seconds()
    server_time = response.json().get("serverTime") / 1000.0 - elapsed_time
    bst = datetime.fromtimestamp(server_time, tz=timezone.utc)
    time_here = time.time()
    delta = server_time - time_here
    print(f"--> Binance serverTime:\t{bst}")
    print(f"--> текущее время:\t\t{datetime.fromtimestamp(time_here, tz=timezone.utc)}")
    print(f"--> рассинхрон: {server_time - time_here: 0.3f}")


""""
Сервер присваивает вес каждому ответу от 1 до N с шагом 1.
На каждой новой минуте счетчик сбрасывается.
За одну минуту можно отправить максимум N запросов с весами 1, 2, ... N сумма всех весов = 1200, N = 48.
1200 это лимит сервера. n^2 +n -2400 = 0 N=48
Из уравнения арифметической прогрессии, считаем, что за одну минуту можно отправит максимум 48 запросов.
Для равномерного распределения запросов по минуте, считываем задержку между отправкой запросов:
sleeping_time = 60/N - среднее_время_запроса  
"""

time_info()
last_hour_info = asyncio.run(get_last_hour_high_price())
close_time = last_hour_info[1]
price_last_hour = last_hour_info[0]
print(f"время закрытия прошлого часа: {datetime.fromtimestamp(close_time).strftime('%H:%M:%S')}")
print(f"максимальная цена прошлого часа: {yellow_ch}{price_last_hour}{reset_ch}")
next_hour_time = close_time + timedelta(minutes=60).seconds
print(f"следующий час закроется в: {datetime.fromtimestamp(next_hour_time).strftime('%H:%M:%S')}")

queries_number_1m = math.sqrt(1 + 8 * MINUTE_LIMIT) / 2 - 0.5
print(f"расчетное количество запросов за 1 мин: {queries_number_1m: 0.3f}")

print(f"\t--> пуск:{datetime.fromtimestamp(time.time()).strftime('%H:%M:%S')}\n")

while True:
    if time.time() >= next_hour_time:
        last_hour_info = asyncio.run(get_last_hour_high_price())
        close_time = last_hour_info[1]
        price_last_hour = last_hour_info[0]
        print(f"время закрытия прошлого часа: {datetime.fromtimestamp(close_time).strftime('%H:%M:%S')}")
        print(f"максимальная цена прошлого часа: {yellow_ch}{price_last_hour}{reset_ch}")
        next_hour_time = close_time + timedelta(minutes=60).seconds
        print(f"следующий час закроется в: {datetime.fromtimestamp(next_hour_time).strftime('%H:%M:%S')}")

    weight_list = []
    time_list = []
    start_time = time.monotonic()
    while time.monotonic() - start_time < 60 and sum(weight_list) < MINUTE_LIMIT - 100:
        price_info = asyncio.run(io_get_price())
        if price_info[0] < price_last_hour * 0.99:
            print(f"{yellow_ch}<--- цена {price_info[0]} упала более чем на 1% "
                  f"от цены {price_last_hour} последнего часа --->{reset_ch}")
        time_list.append(price_info[2])
        weight_list.append(price_info[1])
        sleeping_time = 60 / queries_number_1m - statistics.fmean(time_list) / 10 ** 6
        print(f"{len(weight_list):<4} цена {price_info[0]: 0.4f} "
              f"время запроса: {price_info[2] / 10 ** 6: 0.3f} "
              f"задержка: {sleeping_time: 0.3f} вес {price_info[1]:>5} "
              f"накопленный вес {sum(weight_list)}")
        time.sleep(sleeping_time)
    stop_time = time.monotonic() - start_time
    print(f"время = {stop_time:.3f}, "
          f"среднее время запроса: {statistics.fmean(time_list) / 10 ** 6: 0.3f}, "
          f"кол-во запросов в минуту: {yellow_ch}{len(time_list)}{reset_ch} "
          f"накопленный вес {sum(weight_list)}")
    print(f"-->\t{datetime.fromtimestamp(time.time()).strftime('%H:%M:%S:%f')}")

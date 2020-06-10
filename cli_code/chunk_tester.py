import csv
from pathlib import Path
import psutil
from matplotlib import pylab as plt
import sys
import time

from cli_code.file_handler import prep_upload


def main():
    chunk_list_kib = [4, 8, 16, 32, 64, 68, 72, 76, 80, 84, 88, 92, 96,
                      100, 200, 300, 400, 500]

    chunk_list_bytes = [x*1024 for x in chunk_list_kib]

    file = Path("../files/testfolder/testfile_109.fna")
    file_size = file.stat().st_size

    # 8 cpus

    mem_list = []
    time_list = []
    speed_list = []
    size_list = []
    for x in chunk_list_bytes:
        print(f"\nStarting chunk size {x/1024} KiB...")
        start = time.process_time()

        process = psutil.Process(
            prep_upload(file=file, chunk_size=x)
        )

        end = time.process_time()

        mem_list.append(process.memory_info().rss)
        time_list.append(end-start)
        speed_list.append((file_size/1000000)/time_list[-1])

        enc_file = Path("test_encrypted.xxx")
        size_list.append(file_size/enc_file.stat().st_size)

        if enc_file.exists():
            try:
                enc_file.unlink()
            except Exception as e:
                sys.exit(e)
        print(f"Finished chunk size {x/1024} KiB.\n"
              f"Memory usage: {mem_list[-1]}\n"
              f"Time usage: {time_list[-1]}\n"
              f"Compression ratio: {size_list[-1]}\n\n"
              f"Speed: {speed_list[-1]}")
        time.sleep(10)

    with Path(file.name + ".csv").open(mode='w',  newline='') as csv_file: 
        wr = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
        wr.writerow(["KiB"] + chunk_list_kib)
        wr.writerow(["Time"] + time_list)
        wr.writerow(["Speed"] + speed_list)
        wr.writerow(["Memory usage"] + mem_list)
        wr.writerow(["Compression ratio"] + size_list)

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2)
    ax1.plot(chunk_list_kib, time_list, 'ok-')
    ax1.set_title('Time')
    ax2.plot(chunk_list_kib, mem_list, 'og-')
    ax2.set_title('Memory usage')
    ax3.plot(chunk_list_kib, speed_list, 'ob-')
    ax3.set_title('Speed')
    ax4.plot(chunk_list_kib, size_list, 'oc-')
    ax4.set_title('Compression ratio')

    plt.show()


if __name__ == '__main__':
    main()

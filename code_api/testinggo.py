from ctypes import cdll
lib = cdll.LoadLibrary('./libadd.so')
print("Loaded go generated SO library")
result = lib.add(2, 3)
print(result)
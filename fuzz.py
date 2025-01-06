from thefuzz import fuzz
import time
import random
import string

def generate_random_string(length):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# 生成测试数据
count = 100000
test_strings = [(generate_random_string(10), generate_random_string(10)) for _ in range(count)]

# 测试普通字符串比较
start_time = time.time()
for s1, s2 in test_strings:
    a = (s1 == s2)
str_compare_time = time.time() - start_time

# 测试 fuzz.ratio
start_time = time.time()
for s1, s2 in test_strings:
    fuzz.ratio(s1, s2)
fuzz_time = time.time() - start_time

print(f"字符串比较耗时: {str_compare_time:.4f}秒")
print(f"fuzz.ratio耗时: {fuzz_time:.4f}秒")
print(f"fuzz.ratio比字符串比较慢 {fuzz_time/str_compare_time:.1f}倍")

print(fuzz.ratio("Da.レッスン", "Daレッスン"))
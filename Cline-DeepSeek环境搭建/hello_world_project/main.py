# hello_world_project/main.py
# 故意写得"可重构"的示例：一个混乱的购物车计价函数
# 用途：供 Cline / DeepSeek 重构测试验证用
# 问题点：函数名无意义、无类型注解、魔数硬编码折扣、print 替代返回、可测试性差


def p(items, vip):
    total = 0
    for i in items:
        total = total + i[1] * i[2]
    if vip:
        total = total * 0.8
    else:
        total = total * 0.95
    print("total", total)
    return total


cart = [("apple", 5, 2), ("banana", 3, 4)]
p(cart, True)

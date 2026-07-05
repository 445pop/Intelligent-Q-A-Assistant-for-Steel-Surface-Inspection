import enum

# from XX_infer_project.UtilObject.ProjectConfig import Season

# 定义Season枚举类
Season = enum.Enum('Season2', ('疑似', '警告', '报警', '报警1'))

# 直接访问指定枚举
print(Season.疑似)
# 访问枚举成员的变量名
print(Season.疑似.name)
# 访问枚举成员的值
print(Season.疑似.value)

# 根据枚举变量名访问枚举对象
# print(Season['WINTER']) # Season.WINTER
# 根据枚举值访问枚举对象
print(Season(2).value < Season(3).value) # Season.SUMMER

# 遍历Season枚举的所有成员
for name, member in Season.__members__.items():
    print(name, '=>', member, ',', member.value)

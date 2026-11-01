import pandas as pd
import numpy as np

# 姓名列表
names = ['黄东', '黄尚', '张宏', '戴锋', '吕振', '李将', '俞国', '梁鹏', '田峻', '关燕', '徐白', '张一', '张屏', '于',
         '叶', '毛', '安', '徐', '王宁', '张峰', '刘军', '张书', '徐昊']
agree_totals = [556, 556, 556, 556, 556, 556, 532, 526, 511, 507, 506, 504, 501, 495, 494, 493, 491, 466, 439, 432, 417,
                359, 292]

n_votes = 556
max_choices = 21

# 初始化投票矩阵，所有票对前6个姓名投同意
votes = np.full((n_votes, len(names)), '反对', dtype=object)
votes[:, :6] = '同意'

# 计算每张票已投同意数（前6个）
current_agrees = np.full(n_votes, 6)

# 剩余姓名的同意总数和索引
remaining_names = names[6:]
remaining_agrees = agree_totals[6:]
remaining_indices = list(range(6, len(names)))

# 按同意总数降序排序剩余姓名
sorted_indices = [i for _, i in sorted(zip(remaining_agrees, remaining_indices), reverse=True)]
sorted_agrees = sorted(remaining_agrees, reverse=True)

# 分配剩余姓名的同意票
for idx, total in zip(sorted_indices, sorted_agrees):
    # 计算还需要分配的同意票数
    current_total = np.sum(votes[:, idx] == '同意')
    needed = total - current_total

    # 随机选择票，确保不超过每张票的最大同意数
    candidate_votes = [i for i in range(n_votes) if votes[i, idx] != '同意' and current_agrees[i] < max_choices]
    if len(candidate_votes) < needed:
        # 如果候选票不足，选择所有候选票
        selected = candidate_votes
    else:
        selected = np.random.choice(candidate_votes, needed, replace=False)

    # 更新投票状态
    for vote_idx in selected:
        votes[vote_idx, idx] = '同意'
        current_agrees[vote_idx] += 1

# 分配反对和弃权
for i in range(n_votes):
    for j in range(len(names)):
        if votes[i, j] != '同意':
            votes[i, j] = np.random.choice(['反对', '弃权'], p=[0.5, 0.5])

# 创建DataFrame
df = pd.DataFrame(votes, columns=names)
df.insert(0, '票号', range(1, n_votes + 1))

# 按列统计（每个候选人的同意、反对、弃权数量）
column_stats = []
for name in names:
    col_data = df[name]
    agree_count = (col_data == '同意').sum()
    against_count = (col_data == '反对').sum()
    abstain_count = (col_data == '弃权').sum()
    column_stats.append({
        '候选人': name,
        '同意': agree_count,
        '反对': against_count,
        '弃权': abstain_count,
        '总计': agree_count + against_count + abstain_count
    })

column_stats_df = pd.DataFrame(column_stats)

# 按行统计（每张票的同意、反对、弃权数量）
row_stats = []
for i in range(len(df)):
    row_data = df.iloc[i, 1:]  # 跳过票号列
    agree_count = (row_data == '同意').sum()
    against_count = (row_data == '反对').sum()
    abstain_count = (row_data == '弃权').sum()
    row_stats.append({
        '票号': i + 1,
        '同意': agree_count,
        '反对': against_count,
        '弃权': abstain_count,
        '总计': agree_count + against_count + abstain_count
    })

row_stats_df = pd.DataFrame(row_stats)

# 创建Excel写入器
with pd.ExcelWriter('投票结果_统计.xlsx', engine='openpyxl') as writer:
    # 原始投票数据
    df.to_excel(writer, sheet_name='原始投票数据', index=False)

    # 按列统计
    column_stats_df.to_excel(writer, sheet_name='按候选人统计', index=False)

    # 按行统计
    row_stats_df.to_excel(writer, sheet_name='按票号统计', index=False)

print("完整投票结果已保存为'投票结果_统计.xlsx'")
print("包含三个工作表：")
print("1. 原始投票数据 - 每张票的详细投票情况")
print("2. 按候选人统计 - 每个候选人的同意、反对、弃权数量")
print("3. 按票号统计 - 每张票的同意、反对、弃权数量")

# 验证同意总数是否匹配
print("\n验证同意总数：")
for i, name in enumerate(names):
    actual = (df[name] == '同意').sum()
    target = agree_totals[i]
    status = "✓" if actual == target else f"✗ (目标:{target})"
    print(f"{name}: {actual} {status}")
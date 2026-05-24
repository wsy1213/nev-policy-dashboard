"""
generate_brief.py — 根据当月抓取的数据生成月度简报 JSON
用法: python generate_brief.py [YYYY-MM]
默认生成当月简报，输出到 frontend/public/data/brief.json
"""
import json, glob, sys, os
from datetime import datetime
from collections import defaultdict, Counter

BASE = os.path.dirname(os.path.abspath(__file__))

def load_all(month=None):
    """加载所有数据，可选按月份过滤"""
    pattern = f'{month}-*.json' if month else '2026-*.json'

    policies, industry, intl, media = [], [], [], []
    for f in sorted(glob.glob(os.path.join(BASE, 'data', pattern))):
        with open(f) as fp:
            policies.extend(json.load(fp))
    for f in sorted(glob.glob(os.path.join(BASE, 'data/industry', pattern))):
        with open(f) as fp:
            industry.extend(json.load(fp))
    for f in sorted(glob.glob(os.path.join(BASE, 'data/international', pattern))):
        with open(f) as fp:
            intl.extend(json.load(fp))
    for f in sorted(glob.glob(os.path.join(BASE, 'data/media', pattern))):
        with open(f) as fp:
            media.extend(json.load(fp))
    return policies, industry, intl, media


def group_by(items, key='sub_industry'):
    groups = defaultdict(list)
    for item in items:
        groups[item.get(key, '综合/其他')].append(item)
    return dict(groups)


def _extract_key_numbers(summaries):
    """从摘要中提取关键数据点"""
    import re
    numbers = []
    for s in summaries:
        if not s:
            continue
        # 匹配 "同比增长XX%"、"达到XXX万个"等关键数字
        matches = re.findall(r'[\u4e00-\u9fff]*(?:同比|环比|累计|达到|增长|下降|总数|总量|产量)[^\u3002，。,]*[\d.]+[%\u4e07\u4ebf\u5343\u767e\u5341]*[^\u3002，。,]*', s)
        for m in matches:
            m = m.strip().strip('"').strip()
            if len(m) > 10 and len(m) < 80:
                numbers.append(m)
    return numbers[:3]


def generate_brief(month=None):
    policies, industry, intl, media = load_all(month)
    total = len(policies) + len(industry) + len(intl) + len(media)
    if total == 0:
        return None

    # 日期范围
    all_dates = sorted(set(
        x.get('pub_date', '') for x in [*policies, *industry, *intl, *media] if x.get('pub_date')
    ))
    date_range = {'start': all_dates[0], 'end': all_dates[-1]} if all_dates else None

    # 统计
    p_cat = Counter(p.get('category', '') for p in policies)
    i_src = Counter(i.get('source', '') for i in industry)
    x_src = Counter(i.get('source', '') for i in intl)
    m_src = Counter(i.get('source', '') for i in media)
    sub_counts = Counter(
        x.get('sub_industry', '综合/其他') for x in [*policies, *industry, *intl, *media]
    )
    top_industries = [k for k, v in sub_counts.most_common() if k != '综合/其他']

    # ─── 按版块分组 ───
    p_groups = group_by(policies)
    i_groups = group_by(industry)
    x_groups = group_by(intl)
    m_groups = group_by(media)

    # ─── 生成概览段 ───
    overview_para = (
        f'本月共收集新能源产业相关资讯 **{total}** 条，其中政策法规 **{len(policies)}** 条'
        f'（中央 {p_cat.get("中央法规", 0)} 条、地方 {p_cat.get("地方法规", 0)} 条），'
        f'行业数据 **{len(industry)}** 条，国际动态 **{len(intl)}** 条，'
        f'媒体报道 **{len(media)}** 条。'
    )

    # 行业热度排名
    hot_parts = []
    for ind in top_industries[:4]:
        hot_parts.append(f'**{ind}**（{sub_counts[ind]}）')
    overview_para += f'关注度最高的细分领域依次为{" > ".join(hot_parts)}。'

    # ─── 生成政策动向段 ───
    policy_paras = _build_policy_narrative(p_groups, p_cat)

    # ─── 生成行业数据段 ───
    industry_paras = _build_industry_narrative(i_groups, i_src)

    # ─── 生成国际动态段 ───
    intl_paras = _build_intl_narrative(x_groups, x_src)

    # ─── 生成媒体聚焦段 ───
    media_paras = _build_media_narrative(m_groups, m_src)

    # ─── 组装简报 ───
    brief = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'date_range': date_range,
        'stats': {
            'total': total,
            'policy': len(policies),
            'industry': len(industry),
            'intl': len(intl),
            'media': len(media),
            'central': p_cat.get('中央法规', 0),
            'local': p_cat.get('地方法规', 0),
        },
        'sub_industry_counts': dict(sub_counts.most_common()),
        'sections': [
            {
                'title': '一、概览',
                'paragraphs': [overview_para],
            },
            {
                'title': '二、政策动向',
                'paragraphs': policy_paras,
            },
            {
                'title': '三、行业数据要点',
                'paragraphs': industry_paras,
            },
            {
                'title': '四、国际动态观察',
                'paragraphs': intl_paras,
            },
            {
                'title': '五、媒体聚焦',
                'paragraphs': media_paras,
            },
        ],
    }
    return brief


def _build_policy_narrative(p_groups, p_cat):
    """生成政策综述段落——分析性叙述"""
    paras = []

    # 中央政策重点
    central_items = []
    local_items = []
    for sub, items in p_groups.items():
        for p in items:
            if p.get('category') == '中央法规':
                central_items.append(p)
            else:
                local_items.append(p)

    if central_items:
        bodies = list(set(p.get('issuing_body', '') for p in central_items if p.get('issuing_body')))
        body_str = '、'.join(bodies[:3])

        # 提取关键词主题
        themes = []
        for p in central_items:
            title = p['title']
            if '充电' in title or '换电' in title:
                themes.append('充换电基础设施')
            elif '氢能' in title:
                themes.append('氢能应用')
            elif '新能源汽车' in title or '车辆' in title:
                themes.append('新能源汽车产业')
            elif '光伏' in title:
                themes.append('光伏发电')
            elif '可再生能源' in title or 'IRENA' in title:
                themes.append('可再生能源国际合作')
        themes = list(dict.fromkeys(themes))  # 去重保序

        para = f'中央层面，{body_str}等部门围绕'
        para += '、'.join(f'**{t}**' for t in themes[:3])
        para += f'等方向发布 {len(central_items)} 项政策文件，推动相关产业规范化发展。'
        paras.append(para)

    if local_items:
        # 统计涉及省份
        provinces = set()
        for p in local_items:
            body = p.get('issuing_body', '')
            for prov in ['北京', '上海', '广东', '浙江', '江苏', '山东', '四川', '湖南',
                         '湖北', '河北', '河南', '甘肃', '宁夏', '内蒙古', '重庆', '天津',
                         '福建', '安徽', '江西', '广西', '云南', '贵州', '陕西', '山西',
                         '辽宁', '吉林', '黑龙江', '海南', '新疆', '西藏', '青海']:
                if prov in body or prov in p.get('title', ''):
                    provinces.add(prov)

        local_themes = defaultdict(int)
        for p in local_items:
            sub = p.get('sub_industry', '综合/其他')
            local_themes[sub] += 1

        prov_str = '、'.join(sorted(provinces)[:5])
        theme_str = '、'.join(f'{k}（{v} 条）' for k, v in sorted(local_themes.items(), key=lambda x: -x[1]))

        para = f'地方层面，{prov_str}等 {len(provinces)} 个省份出台 {len(local_items)} 项地方法规，'
        para += f'涵盖{theme_str}等领域。'

        # 找到最突出的地方主题
        top_local_sub = max(local_themes, key=local_themes.get)
        if top_local_sub != '综合/其他':
            para += f'其中**{top_local_sub}**相关政策最为密集，'
            para += '体现出地方政府对该领域的重点推进力度。'
        paras.append(para)

    return paras


def _build_industry_narrative(i_groups, i_src):
    """生成行业数据综述——提炼关键数据"""
    paras = []

    # 总体概述
    src_parts = [f'{src} {cnt} 条' for src, cnt in i_src.most_common(5)]
    paras.append(f'本月行业数据覆盖{" | ".join(src_parts)}等权威信源。')

    for sub, items in sorted(i_groups.items(), key=lambda x: -len(x[1])):
        summaries = [i.get('summary', '') for i in items if i.get('summary')]
        titles = [i['title'] for i in items]
        sources = list(set(i.get('source', '') for i in items))

        # 提取关键数字
        key_nums = _extract_key_numbers(summaries)

        if sub == '综合/其他':
            if key_nums:
                para = '**宏观能源数据**方面，' + '；'.join(key_nums) + '。'
            else:
                para = _summarize_titles_as_narrative('宏观能源数据', titles)
        else:
            para = f'**{sub}**方面，'
            if key_nums:
                para += '；'.join(key_nums) + '。'
            else:
                para += _summarize_titles_as_narrative(sub, titles, prefix=False)

        paras.append(para)

    return paras


def _summarize_titles_as_narrative(topic, titles, prefix=True):
    """从标题中提取关键信息，生成叙述性摘要"""
    import re
    # 统计月份提及
    months = set()
    for t in titles:
        m = re.search(r'(\d+)年(\d+)月', t)
        if m:
            months.add(f'{m.group(1)}年{m.group(2)}月')

    # 统计关键主题词
    keywords = []
    for t in titles:
        t_clean = re.sub(r'【[^】]+】', '', t).strip()
        if '深度分析' in t or '市场分析' in t:
            keywords.append('市场深度分析')
        elif '销量' in t or '排名' in t:
            keywords.append('产销数据排名')
        elif '运行' in t:
            keywords.append('运行情况')
        elif '停运' in t or '故障' in t or 'PCS' in t:
            keywords.append('设备运行可靠性')
        elif '产量' in t:
            # 提取具体数据
            num_match = re.search(r'增长[\d.]+%', t)
            if num_match:
                keywords.append(f'产量{num_match.group()}')
            else:
                keywords.append('产量数据')
        elif '签约' in t or '投资' in t:
            keywords.append('项目签约投资')
        elif '经济运行' in t:
            keywords.append('经济运行情况')
        elif '充电' in t or '充换电' in t:
            keywords.append('充电设施建设')

    # 去重保序
    keywords = list(dict.fromkeys(keywords))[:4]

    month_str = '、'.join(sorted(months)[:2]) + '份' if months else '近期'
    kw_str = '、'.join(keywords) if keywords else '行业最新进展'

    text = f'{month_str}{kw_str}等内容，共发布 {len(titles)} 篇报告。'

    if prefix:
        return f'**{topic}**方面，{text}'
    else:
        return text


def _extract_subject(title):
    """从标题提取主语关键词"""
    import re
    title = re.sub(r'【[^】]+】', '', title).strip()
    if '：' in title:
        title = title[:title.index('：')]
    if len(title) > 20:
        title = title[:20]
    return title


def _build_intl_narrative(x_groups, x_src):
    """生成国际动态综述——提炼主题与趋势"""
    paras = []

    # 总体概述
    src_parts = [f'**{src}**（{cnt} 条）' for src, cnt in x_src.most_common()]
    paras.append(f'本月国际动态主要来自{" ".join(src_parts)}。')

    for sub, items in sorted(x_groups.items(), key=lambda x: -len(x[1])):
        titles = [i['title'] for i in items]

        if sub == '综合/其他':
            # 分析主要主题
            themes = defaultdict(list)
            for t in titles:
                if '中东' in t or '石油' in t or '原油' in t:
                    themes['中东局势与能源安全'].append(t)
                elif '天然气' in t or 'LNG' in t:
                    themes['天然气市场'].append(t)
                elif '核' in t:
                    themes['核能复兴'].append(t)
                elif 'IEA' in t and ('执行' in t or '部长' in t or '声明' in t):
                    themes['国际能源治理'].append(t)
                elif '数据中心' in t or '发电' in t or '电力' in t:
                    themes['电力与算力需求'].append(t)
                elif 'CCUS' in t or '碳' in t:
                    themes['碳捕集与减排'].append(t)
                elif '铜' in t or '供应链' in t:
                    themes['关键矿产与供应链'].append(t)
                else:
                    themes['其他'].append(t)

            # 取 top 主题
            topic_parts = []
            for theme, ts in sorted(themes.items(), key=lambda x: -len(x[1])):
                if theme == '其他':
                    continue
                if len(ts) >= 2:
                    topic_parts.append(f'**{theme}**（{len(ts)} 条）')
                elif len(ts) == 1:
                    topic_parts.append(f'**{theme}**')
                if len(topic_parts) >= 4:
                    break

            if topic_parts:
                para = f'综合领域共 {len(items)} 条报道，核心议题集中在{"、".join(topic_parts)}等方向。'
            else:
                para = f'综合领域共 {len(items)} 条报道，涵盖全球能源市场多个热点议题。'

            # 补充标志性事件的内容描述
            notable = []
            for t in titles:
                if '有史以来' in t or '创' in t or '新高' in t or '最大' in t:
                    notable.append(t)
            if notable:
                # 概括而非引用标题
                if any('新高' in n for n in notable):
                    para += '多项指标创下历史新高，反映出全球能源格局正经历深刻调整。'
                elif any('最大' in n for n in notable):
                    para += '部分领域出现历史性举措，显示国际能源合作力度加大。'

            paras.append(para)
        else:
            # 具体行业——从标题提炼内容而非罗列
            para = f'**{sub}**领域，'
            summaries_intl = [i.get('summary', '') for i in items if i.get('summary')]
            key_nums = _extract_key_numbers(summaries_intl)
            if key_nums:
                para += '；'.join(key_nums) + '。'
            else:
                # 从标题中提炼趋势
                trends = []
                for t in titles:
                    if '增长' in t or '增加' in t or '新高' in t:
                        trends.append('增长')
                    elif '下降' in t or '减少' in t:
                        trends.append('下行')
                if trends:
                    trend_word = '整体呈上升态势' if trends.count('增长') > trends.count('下行') else '出现分化趋势'
                    para += f'共收录 {len(items)} 条动态，{trend_word}。'
                else:
                    para += f'共收录 {len(items)} 条动态，涵盖行业最新发展。'
            paras.append(para)

    return paras


def _build_media_narrative(m_groups, m_src):
    """生成媒体聚焦综述段落"""
    paras = []

    # 总体概述
    src_parts = [f'**{src}**（{cnt} 条）' for src, cnt in m_src.most_common()]
    if src_parts:
        paras.append(f'本月媒体报道来源分布：{"、".join(src_parts)}。')

    for sub, items in sorted(m_groups.items(), key=lambda x: -len(x[1])):
        titles = [i['title'] for i in items]
        sources = list(set(i.get('source', '') for i in items))

        if sub == '综合/其他':
            para = f'**综合领域**共 {len(items)} 篇报道，'
        else:
            para = f'**{sub}**领域，'

        # 从标题提取关键主题
        themes = []
        for t in titles:
            if '产能' in t or '过剩' in t:
                themes.append('产能问题')
            elif '出口' in t or '海外' in t or '出海' in t:
                themes.append('海外市场')
            elif '价格' in t or '降价' in t or '内卷' in t:
                themes.append('价格竞争')
            elif '技术' in t or '突破' in t or '创新' in t:
                themes.append('技术创新')
            elif '投资' in t or '融资' in t or 'IPO' in t:
                themes.append('资本动向')
            elif '政策' in t or '补贴' in t:
                themes.append('政策解读')
        themes = list(dict.fromkeys(themes))[:3]

        if themes:
            para += f'媒体关注焦点集中在{"、".join(themes)}等议题，共 {len(items)} 篇。'
        else:
            para += f'共收录 {len(items)} 篇报道，涵盖行业最新动态。'

        paras.append(para)

    return paras


if __name__ == '__main__':
    month = sys.argv[1] if len(sys.argv) > 1 else None
    brief = generate_brief(month)
    if brief is None:
        print('没有找到数据，无法生成简报。')
        sys.exit(1)

    out_path = os.path.join(BASE, 'frontend', 'public', 'data', 'brief.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(brief, f, ensure_ascii=False, indent=2)

    print(f'简报已生成: {out_path}')
    print(f'共 {brief["stats"]["total"]} 条数据，{len(brief["sections"])} 个板块')


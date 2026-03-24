"""
코어 워치리스트 - 투자 관심 종목 및 테마 키워드
"""

WATCHLIST = {
    # ===== 미국/글로벌 개별 종목 =====
    'Palantir': ['PLTR', 'Palantir', 'palantir', 'Ontology', 'Maven', 'AIPCon'],
    'Rocket Lab': ['RKLB', 'Rocket Lab', 'rocket lab', 'Neutron', 'Electron', 'SolAero'],
    'Bloom Energy': ['BE', 'Bloom Energy', 'bloom energy', 'fuel cell', 'solid oxide'],
    'Planet Labs': ['PL', 'Planet Labs', 'planet labs', 'earth observation'],
    'Cheniere Energy': ['LNG', 'Cheniere', 'cheniere', 'Sabine Pass', 'Corpus Christi'],
    'Anduril': ['Anduril', 'anduril', 'Lattice', 'Palmer Luckey'],
    'SpaceX': ['SpaceX', 'spacex', 'Starshield', 'Starlink', 'Starship'],
    'Robinhood': ['HOOD', 'Robinhood', 'robinhood'],
    'Tesla': ['TSLA', 'Tesla', 'tesla', 'Elon Musk'],
    'Google': ['GOOGL', 'GOOG', 'Google', 'Alphabet', 'DeepMind', 'Gemini'],
    'NVIDIA': ['NVDA', 'NVIDIA', 'Nvidia', 'nvidia', 'Jensen Huang', 'H100', 'H200', 'B100', 'B200', 'GB200', 'Blackwell'],
    'AMD': ['AMD', 'amd', 'MI300', 'MI400', 'MI455X', 'Lisa Su'],
    'Microsoft': ['MSFT', 'Microsoft', 'Azure', 'Copilot'],
    'Amazon': ['AMZN', 'Amazon', 'AWS'],
    'Meta': ['META', 'Meta Platforms', 'Llama', 'Zuckerberg'],
    'IonQ': ['IONQ', 'IonQ', 'ionq', 'Skyloom'],
    'Micron': ['MU', 'Micron', 'micron'],
    'SanDisk': ['SanDisk', 'Western Digital', 'WDC'],

    # ===== 신규 추가: 반도체/광통신 =====
    'Broadcom': ['AVGO', 'Broadcom', 'broadcom', 'Hock Tan', 'VMware'],
    'Marvell': ['MRVL', 'Marvell', 'marvell', 'custom ASIC'],
    'Lumentum': ['LITE', 'Lumentum', 'lumentum', 'optical transceiver', 'EML'],
    'Coherent': ['COHR', 'Coherent', 'coherent', 'II-VI', 'silicon carbide', 'SiC'],

    # ===== 방산/우주 글로벌 =====
    'Rheinmetall': ['Rheinmetall', 'rheinmetall'],
    'BAE Systems': ['BAE Systems', 'BAE', 'bae systems'],
    'Thales': ['Thales', 'thales'],
    'Leonardo': ['Leonardo', 'leonardo', 'Leonardo DRS'],
    'Lockheed Martin': ['Lockheed Martin', 'Lockheed', 'LMT', 'F-35'],
    'Northrop Grumman': ['Northrop Grumman', 'Northrop', 'NOC', 'B-21'],
    'RTX': ['RTX', 'Raytheon', 'raytheon', 'Patriot'],
    'L3Harris': ['L3Harris', 'l3harris'],
    'General Dynamics': ['General Dynamics', 'GD'],
    'Mynaric': ['Mynaric', 'mynaric', 'OISL', 'optical inter-satellite'],

    # ===== 한국 =====
    'SK Hynix': ['SK Hynix', 'SK하이닉스', 'SKH', '하이닉스', 'Hynix', 'HBM'],
    'Samsung Electronics': ['Samsung', '삼성전자', 'SSNLF', 'Samsung Foundry', 'Samsung Electronics'],
    'Hanwha Aerospace': ['Hanwha Aerospace', '한화에어로스페이스', 'Hanwha Defense', 'Hanwha Ocean'],
    'LIG Nex1': ['LIG Nex1', '천궁', 'Cheongung', 'LIG넥스원'],

    # ===== 테마: 반도체/AI =====
    'HBM': ['HBM', 'HBM4', 'HBM3E', 'High Bandwidth Memory'],
    'AI Inference': ['AI inference', 'inference', 'LLM', 'large language model', 'GPT', 'generative AI'],
    'AI Chip': ['AI chip', 'AI accelerator', 'GPU', 'TPU', 'NPU', 'custom silicon'],
    'Semiconductor': ['semiconductor', 'foundry', 'TSMC', 'chip', 'wafer', 'EUV', 'fab', 'chipmaker'],
    'CPO': ['co-packaged optics', 'CPO', 'optical transceiver', '800G', '1.6T'],

    # ===== 테마: 방산/우주 =====
    'Defense': ['defense', 'defence', 'military', 'Pentagon', 'NATO', 'rearmament', 'arms', 'missile', 'hypersonic', 'Dark Eagle', 'ICBM', 'munition'],
    'Space': ['space', 'satellite', 'orbit', 'launch vehicle', 'constellation', 'SDA', 'Space Force', 'PWSA', 'Golden Dome', 'SHIELD'],
    'European Defense': ['European defence', 'EU defense', 'IRIS-T', 'GOVSATCOM', 'EU SAFE', 'European rearmament'],
    'Drone': ['drone', 'UAV', 'unmanned', 'autonomous weapon', 'loitering munition', 'FPV'],

    # ===== 테마: 에너지 =====
    'Energy': ['energy', 'power grid', 'power plant', 'electricity', 'utility'],
    'LNG Market': ['LNG', 'liquefied natural gas', 'natural gas', 'Hormuz', 'Qatar', 'gas pipeline'],
    'Nuclear': ['nuclear', 'SMR', 'small modular reactor', 'uranium', 'nuclear fusion'],
    'Data Center Power': ['data center', 'data centre', 'hyperscaler', 'power demand', 'colocation'],

    # ===== 테마: 지정학/거시 =====
    'Geopolitics': ['geopolitics', 'sanction', 'tariff', 'trade war', 'decoupling', 'export control'],
    'China': ['China', 'Beijing', 'Xi Jinping', 'CCP', 'Chinese'],
    'Iran': ['Iran', 'Tehran', 'Strait of Hormuz', 'Persian Gulf', 'IRGC'],
    'Russia-Ukraine': ['Ukraine', 'Russia', 'Kyiv', 'Moscow', 'Crimea'],
    'US Politics': ['White House', 'Congress', 'Trump', 'Biden', 'Federal Reserve', 'Fed rate'],
}


def is_watchlist_item(text: str) -> tuple:
    """
    텍스트에서 워치리스트 종목 감지

    Returns:
        (감지_여부, 종목명)
    """
    if not text:
        return False, ""

    text_lower = text.lower()

    for item_name, keywords in WATCHLIST.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return True, item_name

    return False, ""

"""섹터별 비교군 로스터.

DB의 `company` 테이블이 비교군 후보의 1차 출처지만, DB 미연결 폴백 시에는 후보를 알 수 없다.
이 모듈은 Phase 1 데모 범위(반도체 섹터)에서 검증된 종목 코드를 번들 정적 데이터로 제공해
폴백 경로에서도 같은 섹터 peer 후보를 구성할 수 있게 한다.

- 외부 의존 없음(순수 데이터) → 테스트·CI에서 그대로 사용 가능.
- corp_code는 DART 조회용이며 폴백 비교에는 사용하지 않으므로, 확인된 종목만 채우고 나머지는 빈 문자열.
- 실데이터(시세·밸류에이션)는 `peer_data_server`가 pykrx로 별도 조회한다.
"""

from __future__ import annotations

# 섹터 표기는 DB `company.sector`와 동일하게 한국어 "반도체"를 기준으로 한다.
SEMICONDUCTOR = "반도체"

# {sector: [{corp_code, stock_code, corp_name}]}
_ROSTER: dict[str, list[dict[str, str]]] = {
    SEMICONDUCTOR: [
        {"corp_code": "00126380", "stock_code": "005930", "corp_name": "삼성전자"},
        {"corp_code": "00164779", "stock_code": "000660", "corp_name": "SK하이닉스"},
        {"corp_code": "00126447", "stock_code": "000990", "corp_name": "DB하이텍"},
        {"corp_code": "", "stock_code": "042700", "corp_name": "한미반도체"},
        {"corp_code": "", "stock_code": "240810", "corp_name": "원익IPS"},
        {"corp_code": "", "stock_code": "058470", "corp_name": "리노공업"},
        {"corp_code": "", "stock_code": "357780", "corp_name": "솔브레인"},
    ],
}

# 섹터를 알 수 없을 때 반도체 로스터로 매핑하기 위한 별칭(영문/소문자 입력 방어).
_SECTOR_ALIASES: dict[str, str] = {
    "반도체": SEMICONDUCTOR,
    "semiconductor": SEMICONDUCTOR,
    "semi": SEMICONDUCTOR,
}


def normalize_sector(sector: str | None) -> str | None:
    if not sector:
        return None
    return _SECTOR_ALIASES.get(sector.strip().lower(), sector.strip())


def get_sector_roster(sector: str | None) -> list[dict[str, str]]:
    """섹터 로스터를 반환한다. 미지원 섹터는 빈 리스트."""
    normalized = normalize_sector(sector)
    if normalized is None:
        return []
    return [dict(entry) for entry in _ROSTER.get(normalized, [])]


def roster_with_target(sector: str | None, stock_code: str) -> list[dict[str, str]]:
    """대상 종목을 포함한 비교군 후보 코드 목록을 반환한다.

    대상이 로스터에 없으면(예: 비반도체 종목) 대상만 단독으로 포함한다.
    """
    roster = get_sector_roster(sector)
    codes = {entry["stock_code"] for entry in roster}
    if stock_code not in codes:
        roster = [{"corp_code": "", "stock_code": stock_code, "corp_name": stock_code}, *roster]
    return roster

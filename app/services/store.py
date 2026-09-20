from app.config import get_settings
from app.schemas import Analysis, ProgressEvent

_analyses: dict[str, Analysis] = {}


def delete(analysis_id: str) -> None:
    _analyses.pop(analysis_id, None)
    path = get_settings().data_dir / f"{analysis_id}.json"
    if path.exists():
        path.unlink()


def save(analysis: Analysis) -> None:
    _analyses[analysis.id] = analysis
    path = get_settings().data_dir / f"{analysis.id}.json"
    path.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")


def get(analysis_id: str) -> Analysis | None:
    if analysis_id in _analyses:
        return _analyses[analysis_id]
    path = get_settings().data_dir / f"{analysis_id}.json"
    if path.exists():
        analysis = Analysis.model_validate_json(path.read_text(encoding="utf-8"))
        _analyses[analysis_id] = analysis
        return analysis
    return None


def progress(
    analysis: Analysis,
    step: str,
    message: str,
    current: int | None = None,
    total: int | None = None,
) -> None:
    analysis.progress.append(
        ProgressEvent(step=step, message=message, current=current, total=total)
    )
    save(analysis)

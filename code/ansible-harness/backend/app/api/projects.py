"""Project discovery API routes — listing of projects, playbooks, and inventories."""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.projects import InventoryItem, PlaybookItem, ProjectItem
from app.services.ansible_service import get_inventories, get_playbooks, get_projects

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectItem])
def list_projects():
    """사용 가능한 프로젝트 목록을 조회합니다."""
    return get_projects()


@router.get("/{project_name}/playbooks", response_model=list[PlaybookItem])
def list_project_playbooks(project_name: str):
    """프로젝트 내 플레이북 목록을 조회합니다."""
    playbooks = get_playbooks(project_name)
    if not playbooks and not any(p["name"] == project_name for p in get_projects()):
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")
    return playbooks


@router.get("/{project_name}/inventories", response_model=list[InventoryItem])
def list_project_inventories(project_name: str):
    """프로젝트 내 인벤토리 파일 목록을 조회합니다."""
    return get_inventories(project_name)


import shutil
import tempfile
import zipfile
import tarfile
from pathlib import Path
from fastapi import UploadFile, File

@router.post("/{project_name}/upload")
async def upload_project(project_name: str, file: UploadFile = File(...)):
    """프로젝트 코드를 압축 파일(.zip, .tar.gz) 형태로 업로드하여 압축을 풉니다.
    기존에 동일한 프로젝트가 있다면 덮어씁니다 (기존 파일 삭제 후 압축 해제)."""
    
    if not file.filename.endswith((".zip", ".tar.gz", ".tgz")):
        raise HTTPException(status_code=400, detail="Only .zip, .tar.gz, .tgz files are supported")

    from app.services.ansible_service import _get_project_dir
    project_dir = _get_project_dir(project_name)
    
    # 덮어쓰기: 기존 디렉토리가 있으면 삭제
    if project_dir.exists():
        shutil.rmtree(project_dir)
        
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # 임시 디렉토리에 저장 후 해제
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / file.filename
        with tmp_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        try:
            if file.filename.endswith(".zip"):
                with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                    zip_ref.extractall(project_dir)
            elif file.filename.endswith((".tar.gz", ".tgz")):
                with tarfile.open(tmp_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(project_dir)
                    
            # 압축을 풀었을 때 최상위에 폴더 하나만 있다면 (예: myproject-main/) 내부의 파일들을 위로 끌어올림
            items = list(project_dir.iterdir())
            if len(items) == 1 and items[0].is_dir():
                sub_dir = items[0]
                for item in sub_dir.iterdir():
                    shutil.move(str(item), str(project_dir))
                sub_dir.rmdir()
                
        except Exception as e:
            if project_dir.exists():
                shutil.rmtree(project_dir)
            raise HTTPException(status_code=500, detail=f"Failed to extract project: {str(e)}")

    return {"message": "Project uploaded successfully", "project_name": project_name}

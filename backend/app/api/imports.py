"""数据导入 API"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
import tempfile
import os

from app.db.session import get_db_session
from app.services.import_service import import_podcasts_from_excel

router = APIRouter(prefix="/api/imports", tags=["imports"])


@router.post("/excel")
async def import_excel(
    file: UploadFile = File(...),
    skip_existing: bool = True,
    session: AsyncSession = Depends(get_db_session),
):
    """
    从 Excel 文件导入播客数据
    
    支持的格式: .xlsx, .xls
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="只支持 Excel 文件 (.xlsx, .xls)")
    
    # 保存临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        result = await import_podcasts_from_excel(
            tmp_path,
            session,
            skip_existing=skip_existing
        )
        return result
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)



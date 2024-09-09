from fastapi import HTTPException
from starlette import status
from starlette.responses import Response


def get_delete_response(success: bool, table_name):
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'{table_name} record was not found')
    return Response(status_code=status.HTTP_200_OK, content=f'The {table_name} record has been deleted.')
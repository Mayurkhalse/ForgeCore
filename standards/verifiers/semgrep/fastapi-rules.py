# ruff: noqa: F821
# ok: fastapi-no-db-in-routes
@router.post("/users")
async def create(body: UserCreate, svc: UserService = Depends(get_user_service)):
    return await svc.create(body)


# ok: fastapi-no-db-in-routes
@router.get("/users/{user_id}")
async def get_user(user_id: int, svc: UserService = Depends(get_user_service)):
    return await svc.get_by_id(user_id)


# ruleid: fastapi-no-db-in-routes
@router.post("/users")
async def create_bad(body: UserCreate, db: Session = Depends(get_db)):
    db.add(User(**body.dict()))
    db.commit()


# ruleid: fastapi-no-db-in-routes
@router.get("/users")
def list_bad(db: Session = Depends(get_db)):
    db.add(User())
    return []


# ruleid: fastapi-no-db-in-routes
@router.get("/items")
async def query_bad(db: Session = Depends(get_db)):
    return db.query(Item).all()

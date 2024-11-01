def insert_into_db(db, new_rows):
    """Insert new object to the db"""
    try:
        for row in new_rows:
            db.session.add(row)
        db.session.commit()
    except:
        db.session.rollback()
        raise ValueError("Insertion failed")


def delete_from_db(db, rows):
    """Delete row from the db"""
    try:
        for row in rows:
            db.session.delete(row)
        db.session.commit()
    except:
        db.session.rollback()
        raise ValueError("Insertion failed")

from models import new_order,new_partner


def sample_inputs():
    order=new_order('O-7','R-2','Z-9',10)
    p1=new_partner('P-2','Z-1'); p1.update(workload_minutes=5,active_order_ids=['OLD-1'])
    p2=new_partner('P-1','Z-3'); p2.update(workload_minutes=2)
    travel={('Z-1','R-2'):8,('R-2','Z-9'):12,('Z-3','R-2'):12}
    return order,[p1,p2],travel

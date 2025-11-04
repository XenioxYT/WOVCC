import requests, time
API='http://127.0.0.1:5000/api'
email=f'pre{int(time.time())}@test.com'
print('Creating pre-register for', email)
r=requests.post(API+'/auth/pre-register', json={'name':'Pre User','email':email,'password':'testpwd','newsletter':False})
print('Status', r.status_code, r.text)
if r.status_code==200:
    data=r.json()
    sess=data.get('session_id')
    pending=data.get('pending_id')
    print('pending',pending,'session',sess)
    payload={'id':'evt_test','type':'checkout.session.completed','data':{'object':{'id':sess,'payment_status':'paid','metadata':{'pending_id':str(pending)}}}}
    w=requests.post(API+'/payments/webhook', json=payload)
    print('webhook', w.status_code, w.text)
    # Try login
    time.sleep(1)
    l=requests.post(API+'/auth/login', json={'email':email,'password':'testpwd'})
    print('login', l.status_code, l.text)
else:
    print('Pre-register failed')

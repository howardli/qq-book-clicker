#coding=utf-8
import sys, codecs, os, traceback, formatter, string, random, time, urllib2, cookielib, hashlib, binascii, base64
from bs4 import BeautifulSoup
from urlparse import urlparse

file_path = os.path.normpath(os.path.dirname(__file__))
config_path = os.path.join(file_path, 'config')
session_path = os.path.join(file_path, 'session')
captcha_path = os.path.join(file_path, 'captcha')
log_path = os.path.join(file_path, 'log')

#记录日志
def wirte_log(exc_info):
    try:
        log_file = codecs.open(os.path.join(log_path, 'log.' + time.strftime('%Y-%m-%d', time.localtime())), 'a', 'utf-8')
        print exc_info[0], exc_info[1]
        exc = "".join(traceback.format_exception(*exc_info))
        log_file.write(exc)
    finally:
        l = locals()
        if 'log_file' in l:
            log_file.close()

#打开相应的url
def open(url, main_url, cookies, min_time, max_time):
    try:
        is_main =(url == main_url)
        if is_main:
            random_time = 0
        else:
            random_time = stop_time(min_time, max_time)
        request = urllib2.Request(url)
        request.add_header('Referer', main_url)
        request.add_header('Host', urlparse(url).hostname)
        cookies.add_cookie_header(request)
        wp = urllib2.urlopen(request)
        content = wp.read()
        if not is_main:
            record_url(url, main_url)
        soup = BeautifulSoup(content, from_encoding = 'gbk')
        book_title = soup.findAll("p", {"class" : "ctitle"})
        print u'访问:%s,耗时:%sms'%(url, random_time)
        if not is_main:
            if book_title:
                print u'标题:%s'%book_title[0].b.string
            else:
                print u'不能正常打开:%s'%url
        return content
    except:
        wirte_log(sys.exc_info())
    finally:
        l = locals()
        if 'wp' in l:
            wp.close()
        if 'content' in l:
            return content

#记录当前读到的页面
def record_url(url, main_url):
    try:
        url_file = codecs.open(os.path.join(config_path, 'url.txt'), 'r', 'utf-8')
        urls = url_file.readlines()
        temp_file = codecs.open(os.path.join(config_path, 'temp.txt'), 'w', 'utf-8')
        write_line = ''
        for old_url in urls:
            old_url = old_url.strip('\r\n')
            if (url == ''):
                continue;
            if old_url.find(main_url) >= 0:
                write_line += (main_url + ' ' + url + '\r\n')
            else:
                write_line += (old_url + '\r\n')
        write_line = write_line.strip('\r\n')
        temp_file.write(write_line)
    except:
        wirte_log(sys.exc_info())
    finally:
        l = locals()
        if 'url_file' in l:
            url_file.close()
        if 'temp_file' in l:
            temp_file.close()
    os.remove(os.path.join(config_path, 'url.txt'))
    os.rename(os.path.join(config_path, 'temp.txt'), os.path.join(config_path, 'url.txt'))

#暂停的时间
def stop_time(min_time, max_time):
    random_time = random.randint(min_time, max_time)
    time.sleep(random_time / 1000)
    return random_time

#登陆qq
def login(user, password):
    cookiefile = os.path.join(session_path, user + '.' + time.strftime('%Y-%m-%d', time.localtime()))
    cookies = cookielib.MozillaCookieJar(cookiefile)
    while True:
        try:
            cookies.load(ignore_discard=True, ignore_expires=True)
            break
        except:
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))
            opener.addheaders = [('Accept', 'text/html, application/xhtml+xml, */*'),
                            ('Accept-Language', 'zh-CN'),
                            ("Connection", "Keep-Alive"),
                            ("User-Agent", "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0")]
            urllib2.install_opener(opener)
            #构造验证码的url
            verify_url = 'http://check.ptlogin2.qq.com/check?uin=%s&appid=46000101&ptlang=2052&r=%s'%(user, random.random())
            request = urllib2.Request(verify_url)
            response = urllib2.urlopen(request)
            content = response.read().split(',')
            verify_code2 = content[2].split("'")[1]
            if content[0].split('(')[1][1:-1] == '0':
                verify_code1 = content[1][1:-1]
            else:
                print u'有验证码'
                captcha_url = 'http://captcha.qq.com/getimage?aid=46000101&r=%s&uin=%s'%(random.random(), user)
                request = urllib2.Request(captcha_url)
                response = urllib2.urlopen(request)
                captcha_file = codecs.open(os.path.join(captcha_path, '%s.jpg'%user),'wb')
                captcha_file.write(response.read())
                captcha_file.close()
                input_captcha = u'输入验证码:'
                input_captcha = input_captcha.encode('gbk')
                verify_code1 = raw_input(input_captcha)
            #构造登陆的url
            login_url = 'http://ptlogin2.qq.com/login?ptlang=2052'
            login_url += '&u=%s&p='%user
            login_url += get_password(password, verify_code1, verify_code2)
            login_url += '&verifycode=' + verify_code1 + '&low_login_hour=720&aid=46000101&u1=http%3A%2F%2Fmini.t.qq.com%2Finvite%2Fquick.php&ptredirect=3&h=1&from_ui=1&dumy=&fp=loginerroralert&g=1&t=1&dummy='
            req = urllib2.Request(login_url)
            req.add_header('Referer', 'http://t.qq.com/')
            conn = urllib2.urlopen(req)
            login_str = conn.read()
            #print login_str.decode('utf-8')
            if login_str[8] == '0':
                print u'登陆成功'
                cookies.save(cookiefile, ignore_discard=True, ignore_expires=True)
                break
    return cookies

#通过原始密码和两个验证码算出加密密码
def get_password(password, verify_code1, verify_code2):
    password_1 = hashlib.md5(password).digest()
    uin_final = ''
    verify_code2 = verify_code2.split('\\x')
    for i in verify_code2[1:]:
        uin_final += chr(int(i, 16))
    password_2 = hashlib.md5(password_1 + uin_final).hexdigest().upper()
    password_final = hashlib.md5(password_2 + verify_code1.upper()).hexdigest().upper()
    return password_final

#主程序
def main():
    try:
        #读取用户的账号密码
        user_password_file = codecs.open(os.path.join(config_path, 'user.txt'), 'r', 'utf-8')
        user_passwords = user_password_file.readlines()
        #读取程序参数
        param_file = codecs.open(os.path.join(config_path, 'param.txt'), 'r', 'utf-8')
        params = param_file.readlines()
        #读取需要点击的图书url
        url_file = codecs.open(os.path.join(config_path, 'url.txt'), 'r', 'utf-8')
        urls = url_file.readlines()
    except:
        wirte_log(sys.exc_info())
    finally:
        l = locals()
        if 'user_password_file' in l:
            user_password_file.close()
        if 'param_file' in l:
            param_file.close()
        if 'url_file' in l:
            url_file.close()
    #执行读取的程序参数
    for param in params:
        exec param
    for user_password in user_passwords:
        user_password = user_password.strip('\r\n')
        if user_password == '':
            continue;
        up = user_password.split(' ')
        #登陆qq
        cookies = login(up[0], up[1])
        for url in urls:
            url = url.strip('\r\n')
            if url == '':
                continue;
            url_list = url.split(' ')
            read_url = url_list[0]
            break_url = ''
            if len(url_list) > 1:
                break_url = url_list[1]
            content = open(read_url, read_url, cookies, min_time, max_time)
            soup = BeautifulSoup(content)
            book_detail = soup.find(id = "book_detail")
            ols = book_detail.findAll("ol", {"class" : "clearfix"})
            for ol in ols:
                for link in ol.find_all('a'):
                    href_url = link.get('href')
                    full_url = 'http://bookapp.book.qq.com' + href_url
                    if full_url == break_url:
                        break_url=''
                    elif(break_url==''):
                        open(full_url, read_url, cookies, min_time, max_time)

if __name__ == '__main__':
    main()
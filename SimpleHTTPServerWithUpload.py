#!/usr/bin/env python3
 
"""Simple HTTP Server With Upload.

This module builds on http.server by implementing the standard GET
and HEAD requests in a fairly straightforward manner.

see: https://gist.github.com/UniIsland/3346170
"""
 
 
__version__ = "0.1"
__all__ = ["SimpleHTTPRequestHandler"]
__author__ = "bones7456"
__home_page__ = "https://gist.github.com/UniIsland/3346170"
 
import os, sys
import os.path, time
import posixpath
import http.server
import socketserver
import urllib.request, urllib.parse, urllib.error
import html
import shutil
import mimetypes
import re
import argparse
import base64

from io import BytesIO

def fbytes(B):
   'Return the given bytes as a human friendly KB, MB, GB, or TB string'
   B = float(B)
   KB = float(1024)
   MB = float(KB ** 2) # 1,048,576
   GB = float(KB ** 3) # 1,073,741,824
   TB = float(KB ** 4) # 1,099,511,627,776

   if B < KB:
      return '{0} {1}'.format(B,'Bytes' if 0 == B > 1 else 'Byte')
   elif KB <= B < MB:
      return '{0:.2f} KB'.format(B/KB)
   elif MB <= B < GB:
      return '{0:.2f} MB'.format(B/MB)
   elif GB <= B < TB:
      return '{0:.2f} GB'.format(B/GB)
   elif TB <= B:
      return '{0:.2f} TB'.format(B/TB)

class SimpleHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
 
    """Simple HTTP request handler with GET/HEAD/POST commands.

    This serves files from the current directory and any of its
    subdirectories.  The MIME type for files is determined by
    calling the .guess_type() method. And can reveive file uploaded
    by client.

    The GET/HEAD/POST requests are identical except that the HEAD
    request omits the actual contents of the file.

    """
 
    server_version = "SimpleHTTPWithUpload/" + __version__
 
    def do_GET(self):
        """Serve a GET request."""
        f = self.send_head()
        if f:
            self.copyfile(f, self.wfile)
            f.close()
 
    def do_HEAD(self):
        """Serve a HEAD request."""
        f = self.send_head()
        if f:
            f.close()
 
    def do_POST(self):
        """Serve a POST request."""
        r, info = self.deal_post_data()
        print((r, info, "by: ", self.client_address))
        f = BytesIO()
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(b"<html>\n<title>Upload Result Page</title>\n")
        f.write(b'<style type="text/css">\n')
        f.write(b'* {font-family: Helvetica; font-size: 16px; }\n')
        f.write(b'a { text-decoration: none; }\n')
        f.write(b'</style>\n')
        f.write(b"<body>\n<h2>Upload Result Page</h2>\n")
        f.write(b"<hr>\n")
        if r:
            f.write(b"<strong>Success!</strong>")
        else:
            f.write(b"<strong>Failed!</strong>")
        f.write(info.encode())
        f.write(("<br><br><a href=\"%s\">" % self.headers['referer']).encode())
        f.write(b"<button>Back</button></a>\n")
        f.write(b"<hr><small>Powered By: bones7456<br>Check new version ")
        f.write(b"<a href=\"https://gist.github.com/UniIsland/3346170\" target=\"_blank\">")
        f.write(b"here</a>.</small></body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if f:
            self.copyfile(f, self.wfile)
            f.close()

    def deal_post_data(self):
        uploaded_files = []   
        content_type = self.headers['content-type']
        if not content_type:
            return (False, "Content-Type header doesn't contain boundary")
        boundary = content_type.split("=")[1].encode()
        remainbytes = int(self.headers['content-length'])
        line = self.rfile.readline()
        remainbytes -= len(line)
        if not boundary in line:
            return (False, "Content NOT begin with boundary")
        while remainbytes > 0:
            line = self.rfile.readline()
            remainbytes -= len(line)
            fn = re.findall(r'Content-Disposition.*name="file"; filename="(.*)"', line.decode())
            if not fn:
                return (False, "Can't find out file name...")
            path = self.translate_path(self.path)
            fn = os.path.join(path, fn[0])
            line = self.rfile.readline()
            remainbytes -= len(line)
            line = self.rfile.readline()
            remainbytes -= len(line)
            try:
                out = open(fn, 'wb')
            except IOError:
                return (False, "<br><br>Can't create file to write.<br>Do you have permission to write?")
            else:
                with out:                    
                    preline = self.rfile.readline()
                    remainbytes -= len(preline)
                    while remainbytes > 0:
                        line = self.rfile.readline()
                        remainbytes -= len(line)
                        if boundary in line:
                            preline = preline[0:-1]
                            if preline.endswith(b'\r'):
                                preline = preline[0:-1]
                            out.write(preline)
                            uploaded_files.append(fn)
                            break
                        else:
                            out.write(preline)
                            preline = line
        return (True, "<br><br>'%s'" % "'<br>'".join(uploaded_files))
 
    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            if not self.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None
        self.send_response(200)
        self.send_header("Content-type", ctype)
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f
 


    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().

        """
        try:
            list = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        enc = sys.getfilesystemencoding()
        list.sort(key=lambda a: a.lower())
        f = BytesIO()
        displaypath = html.escape(urllib.parse.unquote(self.path))
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(b'<html>\n')
        f.write(('<meta http-equiv="Content-Type" '
                 'content="text/html; charset=%s">' % enc).encode(enc))
        f.write(("<title>Directory listing for %s</title>\n" % displaypath).encode(enc))
        f.write(b'<style type="text/css">\n')
        f.write(b'* {font-family: Helvetica; font-size: 16px; }\n')
        f.write(b'a { text-decoration: none; }\n')
        f.write(b'a:link { text-decoration: none; font-weight: bold; color: #0000ff; }\n')
        f.write(b'a:visited { text-decoration: none; font-weight: bold; color: #0000ff; }\n')
        f.write(b'a:active { text-decoration: none; font-weight: bold; color: #0000ff; }\n')
        f.write(b'a:hover { text-decoration: none; font-weight: bold; color: #ff0000; }\n')
        f.write(b'table {\n  border-collapse: separate;\n}\n')
        f.write(b'th, td {\n  padding:0px 10px;\n}\n')
        f.write(b'</style>\n')
        f.write(("<body>\n<h2>Directory listing for %s</h2>\n" % displaypath).encode(enc))
        f.write(b"<hr>\n")
        f.write(b"<form ENCTYPE=\"multipart/form-data\" method=\"post\">")
        f.write(b"<input name=\"file\" type=\"file\" multiple/>")
        f.write(b"<input type=\"submit\" value=\"upload\"/></form>\n")
        f.write(b"<hr>\n")
        f.write(b'<table>\n')
        f.write(b'<tr><td><img src="data:image/gif;base64,R0lGODlhGAAYAMIAAP///7+/v7u7u1ZWVTc3NwAAAAAAAAAAACH+RFRoaXMgaWNvbiBpcyBpbiB0aGUgcHVibGljIGRvbWFpbi4gMTk5NSBLZXZpbiBIdWdoZXMsIGtldmluaEBlaXQuY29tACH5BAEAAAEALAAAAAAYABgAAANKGLrc/jBKNgIhM4rLcaZWd33KJnJkdaKZuXqTugYFeSpFTVpLnj86oM/n+DWGyCAuyUQymlDiMtrsUavP6xCizUB3NCW4Ny6bJwkAOw==" alt="[PARENTDIR]" width="24" height="24"></td><td><a href="../" >Parent Directory</a></td></tr>\n')
        for name in list:
            dirimage = 'data:image/gif;base64,R0lGODlhGAAYAMIAAP///7+/v7u7u1ZWVTc3NwAAAAAAAAAAACH+RFRoaXMgaWNvbiBpcyBpbiB0aGUgcHVibGljIGRvbWFpbi4gMTk5NSBLZXZpbiBIdWdoZXMsIGtldmluaEBlaXQuY29tACH5BAEAAAEALAAAAAAYABgAAANdGLrc/jAuQaulQwYBuv9cFnFfSYoPWXoq2qgrALsTYN+4QOg6veFAG2FIdMCCNgvBiAxWlq8mUseUBqGMoxWArW1xXYXWGv59b+WxNH1GV9vsNvd9jsMhxLw+70gAADs='
            fullname = os.path.join(path, name)
            displayname = linkname = name
            fsize = fbytes(os.path.getsize(fullname))
            created_date = time.ctime(os.path.getctime(fullname))
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                dirimage = 'data:image/png;base64,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'
                displayname = name + "/"
                linkname = name + "/"
                fsize = ''
                created_date = ''
            if os.path.islink(fullname):
                dirimage = 'data:image/gif;base64,R0lGODlhGAAYAPf/AJaWlpqampubm5ycnJ2dnZ6enp+fn6CgoKGhoaKioqOjo6SkpKWlpaampqioqKmpqaqqqqurq6ysrK2tra6urq+vr7CwsLGxsbKysrOzs7S0tLW1tba2tre3t7i4uLm5ubq6uru7u7y8vL29vb6+vr+/v8LCwsPDw8bGxtDQ0NTU1NXV1dbW1tfX19jY2Nra2tzc3N3d3eDg4OHh4eLi4uPj4+Tk5OXl5efn5+np6erq6uvr6+zs7O7u7u/v7/Dw8PHx8fLy8vPz8/T09PX19fb29vf39/j4+Pr6+vv7+/39/f7+/v///wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACwAAAAAGAAYAAAI/wCZCBxIsKDBgwgLrsigwUXChEVGYNBwIYKIJA8LFunwocKGDA8ieMg4kAiHDxRmCGyhIAEKkhtR2iCYYYEAkiNQ3ijYIQGAjDkuVFBJsIcBAhcyttCgoSCQBQcUFMn44gIFEiwE/oAqIAfJIREeQLDAZIeCAwO8IuQRowYSIxQgBFhAoQBatQaFiLCQoQIFCxEMREUwoAEPhEA0dMQwQSwCIEFYpKCR8IfiCjWYgJCr4AhJyx13CFRhQYECGBmRcKwgmmAEBCsyltBQQUfBGwUG4MjoYMOIgjsSIJBAskGGEAR3IEhw4AdJExIeyBCIY/kBHySZLNEwgcGGDQYQNBbPLpAIBgULEhB4AIQ8wRMFBIhQ4j4gADs='
                displayname = name + "@"
            if name.endswith(('.bmp','.gif','.jpg','.png')):
                dirimage = name
            if name.endswith('.avi'):
                dirimage = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAMAAABg3Am1AAADAFBMVEVHcEwAAAD29vbn5+cBAQH4+PgCAgLw8PD19fX29fUCAgLy8vLz8/MAAADs7Ozq6uoAAAAAAAACAgIBAQEBAQEAAAApFRUKCgoCAgICAgICAgICAgICAgLu7e3d3NwGAwP1ysru7u4AAACJiYkBAQEAAAACAgIAAADCRUWDQkJ2Pj7q3t4ODg6srKyXl5cICAgAAAClW1sAAACyYWEAAADMi4sAAADtWVm3Ly/Yz8/OYmLTSkrgSUkbCQn5SUl+PDx6QkIkBQVLHBy7WFh8QECoSkqmNjacICDgVVXVbW3u7u7y8fHt7e329vbr6+vw8PDo9PXr6uro9PX09PT19fXq9/L39/fy8vLz8/PmFQ7o6OiqFhbn5uanFRWcDg6gERGlExO8IiKeDw+sGBivGRmaDQ2YDAyVCgq0HBzOvb23Hh6NBQWTCQmPBgajEhKyGxveNTXRzs7AJCSxbW3j3t7s4+P2RETnOjrEJibKKSnYMDCRCAjS0dG5ICD8UFDyPT3+XV3/YWH/Zmb/ZGSnRES3cXHbNDSnQkLsPj7KLy/4+PjQvr7qe3u8dHTldXXbYGDRa2vwpKTHeHjd09PiOTmiYGC2S0utRUWxSEinY2PsODjmTEzuVFSuZmb9V1ftXl60OTnsgYHtZWXaqqrpVFTkhobp5eXIubnBXV3XkZHSLi7FPDzLQ0PAMTHov7/ZUFDkuLjbOjrZb2/al5e7S0vln5/fnJz6S0vkMjLqoaHAd3fLWFjEt7fUlJTUOjqfNDTFbm7CZWW6T0/RxsawJSWxVlbAiIjv09OvSkrLOzvkw8P38vLQoKDZt7fBmJjPfn7ssLDz2NjPTEzisbH47++eXFz5SUn+WFjcQ0O4YGCwgYHNysrvaWnvZ2e+gYGtWlrs6OjjX1+9UVHAbGzaSkrRurrkycnhvb27KSm/kJDujY25lpbqiYnONTWfXV3mbGyzenrSW1vJqKjCUFCqJyetMjLxaWmpcXHpamruR0fwk5NHcEy02WkA///26ADnAAAxW1SfAAAA/3RSTlMAQP7/DP2h/v7+Ev7+Ff//GhcdXWgeOwRhSk1aZP77V/7zAdtGLVI8/qmq/w+bo4wS/nr+mv4L/v7+/v7+N/6on42r/qr+/v7+/v///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////wD/QP5RdlUsAAAFK0lEQVRIx72WZ1RTZxjHbcDeaC5JRC04giAgKO69Ou28Nzc5nptzk3OJE62toxINBCKIqylYyrYtogVZKqAMK3Xgwr1nW/euu3bPT32e972Jon7wU//nJrkn9/d7n+cdHNKq1f+RIP/ebTHtXvLm5YC2T6e3f5DCB/YJaw1JqPjpYum17F+2rvnZ2foZCesTSIwgfV9JhCRkFSWmuzxVSSUDHFa12qJc+CbSSH31aPhHhrGsyCZkrvgmMW35JvfBKw7G8rggEgEQNizSH4T+EWpRtCVkFn8/H42z51KsQstYMCipI/qDENCJZTUJqy4tXIBG0Q2HTaUSHl0CqQS0jWXZTgFUAL500WI0ynemsJJK5bsE59EhTkFFpsFqfEJMZvHiRWgU70wRJSVizNG1OTXueM+vErYFJWyK0Dkma9iChWiU5lG+jRPYUTdX5YY+8Hjcl6ES8lChMxG6ZZbP/wqNS8gD+96oa6vKXQXVx9pIS0Nrq8ZIEsxEtGm8wmvlid+hUXrj/tqG2vT09FP5S5eeuVcQ794LN4crSngJW7JZrYrw6oo0NIrzto3ODT0TOszlqj7Gwtjvut3D9w1ZE721UkUrMBoq9Cxfnpb4yrC8lJPpa/Il1Zl/XQWevSPyy467t2dXnNh/WJJ8Qg8U2vUs2rQ8rWhnik36J/3gXV7iT9fHew4Ce1JQFkzpiNf0aEeEm+5NZ3fB+REuulwF10eeyn5w4uRh71aQ4WEfWCvDMFR4syZ5+zkHbxGEe676rceP/PApyYe+5NMKPK8IvarXDXIwrKi25BbEx9dnZWXVVlVlNDQ0nEqaM2dkTk70XDgarIb3Vej19YALnIYVRUtuvKe+Ti2s/zE547SgPrRu0qQytXBr+EpyLlDoRoXCC0beahMtls2e+vUC5S0C4QXh1p64lRbSkdmsCG84tIyZ0dhEcfP29RaxLiM5o04Ub99JTS0TLYf2xMVCBVhTs7eC/nUjRwRW3Fzd3NyckZw0/MCBA3dSp/++ZMmSPbHjJq4UWSJwTDc9Cl0YjjNjT+LG61u2bPkM8zFmLs3eQpF0xHFMFypwBrhnrBrbxuTkJFiZSanTp38we8qUOBh94kcTJheyGtgEDrAnhUaCA6/g4xAfP75Q01JozxlJT1ZrYwucjD55/NT3l8Ej7MjItaeCVmuACjxjbSQ48MroExCfNm2ZBh4ynEGrfVLY8Cx85sxlzFMC9mTm+Q0Ujx3nbQb5ebMe8rBp0JFPMJm0ZCv4DYDHxfpGJ/i8WbMeMrgJRq3JRIVgn7DtMXyqF58x41ufEEwFHQikqW3PwkEgDYGgI0JgsA4M3ApzWXPz55AvIV9A4GR8gjlPNgF4XXAgCl2JAAsFS4VHrOVFPzkDEbp6BTSMuN0oPXaFGOknZyS8V5BlnYlO44mYf9tNb3ACJp0seyugAbtnNODDq43Hj9kN++wcd9l510l46EeLPK3QsYMM0WERqGLUZv6Z+/cVU/Z94+0//EpWG/ErHF6HVIeOVPBTDHT2j67Ujq3ZXbdDHrPP8HaTFmmF93sk+NEiKO2Plk1ja1ZrS86/49TuaCIwHd7PJ/hhZCVXa/9anTe7ST4yba6s29Hk/VomkCKE2O1oKE5MTvSuXbvlyrdGyPIgh0Ijb7eHEEHfPhzu7URSapHn3hcJBcLJ4fOP6hceQmaAczYYyN8rDS6oga4RzCIkvF8U/tvtro8YOPjF58jggRH67uSnQEBk1AvPkajIgCDvr5Oh/s+RoQT/Dy5leULYn/1SAAAAAElFTkSuQmCC'
            if name.endswith('.mkv'):
                dirimage = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAMAAABg3Am1AAADAFBMVEVHcEwCAgIAAAD39/f09PQBAQHx8fHz8/P19fX29vbw8PACAgL4+Pju7u4AAADt7e3q6uoAAAAAAAABAQECAgLd3d0KCgoBAQEBAQEBAQECAgIAAAAjGwACAgICAgLu7u4AAAAAAADw8PBtUBEAAADas2KFaC/y8O3RqVjVwI3t49DFwrr08u0ODg6srKyXl5emfDaJiYkICAgAAACJiYl3Wh5/YBQAAAAAAADBpVXb1s7h0KuxmW/CmAfXwGmuiykNCwIRDQGggiYcFQpoUwOJawQ5LgLMsFPZ0sThx2CwjiHk2rm6lyzUybGUdR3d9PHy8vLv7+/r6ur29vbt7e319fX09PTz8/Pr6+vo8O3w7fjn5+f39/fo6Ojw8PDt+Ob4+Pjm5ubOx7iGYB6fdzKjknXSz8qsgjna2trcsViBWx2OZxDl3tKUayrLoEuddgx7VhiGXxmKYyTVqE7RpEx+WBXf2c/HnEmIYRXW1dOBYy++mEvMxLa2k1DVrl7QplHFqXKmiFC5kQm4l1bk2cXYqlDetmLVxaDOv6SJYSGSg2qtiknLpFTiw4CffkKukl2VcS7PwKfdzKG/o27v59mqjl3c1cioiiC1om3l5OOPdkrkz53El0WQaSW/lUW6jkDZr1aXeSiYiGLGn1bVq1TLpV2sm2+mlXCthAmzi0C8nVaVekinfwqGXw+NbS2AXRGxlV3g3denjmGTbQ20jAixoYOafkbKwK6unX20j0yhgkXq6OOvpZTcv1Dv7erAspuchFq5nGeXdTzWy7m9qoiHZxfEso66j0GheQ6lfAugfTqYiXCZcA2mlWCSelO7omKbdzjTt1K1n3mykFR0Uxa6o36MbDXq4cnVtXTVuYCUcznMysfcxJKzkhO/mU/h4N6wmGe1o3+wkEvJsoPGuJy1liLInga4rpOhfCDa0L24l0mujSymhhG5jUDbu3zIrFTv6M7m1bTs2radgE6/t6TLqy+lgT7PrGaoj0LPupTDqn7Goy7Co0eoAAGoAAFHcEwqtqAxAAABAHRSTlMAoUD+/gz//v7+/hL8/xX//xoXHVv9BEhoX2QcO05V8y0L/c48/v7+/v7+/v4Pm6P+1owS38jOepr+/v7+/v7+IiH+ac7Omf7+/v7+/v7+/f/////////////////////////////////////////////////////////////////////////////////////////////////////////+//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8Ai8SznAAABSxJREFUSMe91mdUE1kUB3B3E6ZEgxMxYFkFWUCxt7WX7cUtZ2aTTOacyeQQIiESpAmhN8EFBQEBaa4uzQIIKvauWNa69rb2Xrf38mHfe5lJgocPfNr/eYczJPeXe2feDKRHj/8j3h6jesK8+ZqUt3p2kVEe3mK912jfXiD22ceio4+tX7dl4RmhVxfxHe2FhLdqjEzOynH7iZVxEQkbWm3Rp60sQejEBX/IwftgycaooPDw88VxFo8sGDt3/uKImITWeiuucwdyBEAJ7uvnAcAEH4Jl9ZENq74OR2KJldV0jg6GBSF8JgDg6SPH6ciM+PhEKMwbKh8+nFNZ+XZdXUlbUFBKSkpQzSGCACPpcVzu4+kAdOTq+EUL4hO/Ci85Ejzr0cyFW9Ydj95ssyXFxpoXX8rfRaLTwGkJ4Pb0VVELoGgKe2Gw/LOitLQ0Ly8vPz9/2bJl2yINHSFgLDC2XgSDphWN/e5LIBZF7VC/GDniX5nM4FoHcrmiEFIHR6LxQQi8c3bl3HAoMu+qyejnnz2TyUJcq31ndmoIqSHkeloCb6yMmw9F4l21xrD5+ZN7Ie650/BHJhrJBSbFRUDRtENNkLIjI0OzO41UNXxoodgBw8QO5gQowqw6kiTNsuvZJGlwrbJysrkz6PN6bExMRNxJsF8Gg+Hi/pPZBvdk3fi1MMQxEQB9EEhKiAH7qyc0oMNF8+LlnTpkzattlIF9wGlM4T/YAWytCUustA7dBjH5lzZ2ui+yVvxUaEAdMEwCp2z1Vgxn4c1GpJCWgwShca2ycqJARoBtxpwdJh2vTzbSOCuH4PLQEWfS0tJCxaSlbbzyeREJ7wtMwYjgvdPJDEbrWXhPakouZKdGZTbWzgOpbcyMSlyV/ku4YyKjUQTvWrWMEQj4lMhPrF6dmRH4BUhgRsawwoZbTTsvzCXhNTUyYgfV+0olAjgEBSM/XEqSGtdqz93XRuIIKP0HqyDo688gAB8RXbrGslTnngORbIqGFTv0FYFWySgwGvTA8dTpW5fCJ9a5vjm/J4Kg4SkrtV2CebUvAXNsbFcAzASEXp/6843v9e6pOf8gSUejU3CC3hxqAQmdI7dcBdK1auz0ETmGGnC9HaC/O7g3dEQWDY6cq+Upb3OC/m7AaMQg+T2nqIx2z7YndetZsGnugOOQAD0w7GxOwUHMPbvmfLIQV6B6jnsZKBSKb/eFFivgkbT+/Hj3zZcBBQAaCuQyfb0jDGbt2jVr1lRVVVVeMd7Uw3oAKAQGDqAo1IIBe8m07F9iNscmJdk2n4qGf8hnPpr1+DeMQQ0oasBAALwcAArGn7HPaG9fXly8Mad56tQfPjh3bu/evR/9yIgNqAFeIpAERI74W+yM6xexXgKCQHFIKF2ACTssHYGXYT1HCYLUQRKQ8KZqJXdbq9xxVKk0aU3glWpnvdihnwACp4LGmp5+6/7yZ1m7D+dxe3Zt2rZbm9wC36EoWNVPBLxTcMnDhpdnrNh3bfrR4DtXh3P3S7mtwVI97wK8owlAyTkcdzCXe3Dj6LCMXI6rCNzUXE45Pp53Ah5GcMTSQQkHngqP/97616GdFYJQVnwNVQuoSARqkwkKZCxtglBzSNgzI+ywsL/jtrC9pAINAwpMJjUCqv7jwLEJIZ6v/lTgQ6v5aRUWO89vN/HV29FnOwrGoVvDI2D8RDU6A066tuDiKxRoB7ToinLoLNQTxwfAf7s9VD6Tp7zSjUyZ7KNyfHXw9At4tRsJ8PP0lr6dDPHoRoag8v8ABDRhbfvj544AAAAASUVORK5CYII='
            if name.endswith('.mp4'):
                dirimage = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAMAAABg3Am1AAADAFBMVEVHcEwAAAD29vbq6ur19fXn5+cCAgLv7+8BAQH09PQBAQHt7e3s7Ozz8/Tx8fLz8/MAAAD4+Pju7u7r6+wAAADx8fEAAADp6eoCAgIKCgrp6ekBAQEAAAAAAAA+TF4VGR4CAgJAT2FDU2YBAQECAgICAgLt7e0CAgJBUWMCAgJGV2wBAQHd3d3r6+sCAgIAAADm6OotND4sMzz29vZ0jKxogJ6Vo7ZOY3+1u8J5gYt3iJ6msb09SlsODg7w8PCsrKwDAwOXl5fs7OyFjJYAAAAAAACbqLoCAgKJiYkICAiJiYkAAADh4uKPlp8AAAAAAADv8PDv7/APERS8vb4pMDgcISaNoLdMV2SYorDAxMq3u7+Bk6n09ej39/fw8PD09PX19fXo6Ojv7+/4+Pjy8vPt7e3p6enz8/Px8fHn5+fu7u7s7O3m5ufr6+vq6utIWW5JW3FBUGM9S1w4RFQ8SlpBT2FCUWRWbIZ4k7bT1dhHWGw7SVl0gI/Excdfd5U6R1c6SFg3Q1I1QE9FVWnW2NrAwcNMX3ZddZOKkp05RlVPY3rU19pYbokzPkw/TmBDU2Zuiatlf6B1kbM/TV5GVmrj5ehLXXRYb4xTaIJOYHeLlaFkdoySoLFbcY14hZVmepN7ip02QlBRZH0yPUtga3lEVGhhbn5SZn9odYSOmKXEyc+zvMeOnK2KmKlcc5Ds7e5aZG8xPElWX2ldaHVZcZCdrL9wiKdpg6Rtgpxtf5aGjphtg59IVWZocdRre5DY295Za4FpfZZoeY5jcoTFzNS4vsdveYVrhadhe5tzjbBYYWxxjK9geZmYp7tTaod0iaJgbHyRm6jS1Na2vslecYe/xMi6wsxVaoSEk6XN0NPJzdF4hJJWZXhzhJmBjp59jaKYpLOCkaN/kadve4rKz9bn6u2/x9CFkqJcZnJlepiyt72Kj5aorrVyh6F2kLB4h5mZn6bd3uBfc4zg4uRxgZaptcSvtb27vL2YnKFPXnFzfIeZn6eaoqyMnbKYgADq9ueap7ZGAAABAHRSTlMAQP/+/v6h/gz+Ev7+/v7+Ffz+/hr+F/5gBP1oHhz+OmT+/khMXP1Z/lD+Xfr9VDz+ioz8/v7+/v7+/v7+D/GbHaP0/i8B/UXWjN96/v4smv78L/6Aif7+/v7+/v///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////v/////////////////+cu1cPQAABeNJREFUSMe9lmlUE1cYhu0kaQiZZnCGGEClAoqIUNS6r7hvVdN9O8kkIZmEhISgQEQDLggqBlHZyypVQBCXKgiFgyxqW1s33PcFcd+37uf0u5ME1x/+6ntuZjJ33ufe997vnpN06fJ/yNNljCuS2/tOfeL6Bo1x8XT4Q8eN7Qr6eMqhu3dr65pbGq1tH3Z9XWPHhbKEp/t4mYAWCIxDbybszM4ZlpyyIUnF5SocDV0E6D0tkI13R4TLpAkEQRP4gSFrf1uefXBYWWkSX/EiIGABsBATJrkA4DqVS9NaQ3XNml2IsJUnyRXYS1Ig0SDuVFcA3PwEBGGsHrzuV5ZoTJK/aBbtHl4BM0EkLUEI/NzsgIiqHjx/PiKGNCaJwSZDjbt771f3j1kspzCMXQYhcgC9BaYDNevmI6LmSbxaBtLt3nup+NHF6muVjywn82gUC2JrBb3tQPDQ+jW/IGLwyHi1CHmbr3y7paDg0laZLPNUTlkm+FEkEWEH+k25ufYnRNyrW5F/sWh5QkIlHYadKLLZiirCZNiJYxWQkCvQipzAZ7UJPyPiXnHJgT2ZHf8u37Ilf2tYWEeV5WRO1bNN7a0nZCiSVq0m+rHAwPqdiKgZGT+yfg8s4FpzQXbRNX3bs7ycvOuj9gxAW8DOIBY5gFobEEPOx+uGJiTkd2CyzPM2i6XlFHi5MvuGvQR0G9h88ODOhDrY/0pIU1T1pKXq6dUO2QtyJNKJ+nVjgaJhOQUtcH6wuIKCuqpRFauQ4pxqa2tDdSDUYqn4AzuQl1zWmqSH82CyZNss5y9fLi4pSWksLi7MMptbC89aM2TsDDqdAxh0LLc1SUjQXAV10mbZ/B621VpSckHNlVrN5rN8TDwiDeNCmXWdMwzK2/CpQUTQAgUnB/xcg7Uk5boII8FfKOfqRvjGYuhc6KR8J1D+u0mn1tIKhalsM40Z2lNSrqsxfXtkZKEck/8VGxtlTySXO4DP4yV8uVikFdCSsvuFha0publWq/VwZOCCfe37dkQF+KSzeyrn86V9EeDugZMsQNCSpk2g70ArWP2INHFiDJdgAVLa1x0BfaUqlRxlopXJMHpyVpY5MnJBRuLGtNiomNXpc6Oj7YlUKifAF5IqqVgt0g7IYu3myAWBiRt9faN8fNK9545euEgggiKoSCHfDvR5DpiTkT0Q2WMDAlZ7I/viRSs7gT4OQKNHmdTq8Eh29IzENJQmHdIg+7x5tBol0mucgD8u1POlOrGaF8jafWF4Hxg+Onohsi9ZT4ihCHoh7m8H+ncCEYnInhYbELMawoB9EbKvX9oJ9GcBD38DyiTX6SLSOrdmLhp9JdiXLk1N1ULRIJHB38MO4BSugVJIdZkBjjD2tc5bAv7U1NTvRVIoggZsrwE+sVE+3ulgR+FRGGTfvv1VINho0LChIg6Xlh7eANqx48aNG9u2bdu/f/8PIDUKpDEYg1mgp0cwhzJAKfhwWtDn5Wa/QxEMFIfj0ROA0F4cBMBGqd4E3BqO7nohC/QKdQAcIy7UkAhQvdLi/jwCd1IjxI2cTsCLMRnZZej1q64eXRW+t0KjUi27ha7G8nNHoBstwGhivJwzSCQmCjcINUIyf9cX9bVX7uaTw5su513AyQflf88iUR6cMkkk9hl6dPdSMowJTWLQ5D/VVB7SPLY9bjqjySw9fqYh7sEKjQENb2IYpVf3HnaAp2QkHBNlpKjNR/Gvr+B40+lcI46fvbMv5sv00bOg38SRMErec4CnVEoYjonDqaqkjl+kqHNnzP/w4htOP2xruz3iI+hnJEol7zkQDlIqIRhz5Chz/ALDnDudUdrQcAdiMH/chgu8RB4nEMTjhcMkMI2SB++AjVgWYHiInuGJ7VayliAWcO8/jceLQA260Ae1Zd5Gx3d7B/ueN4093i4h02cEwZZBvSkcFwqFJMnnC78RQxVJEh5xnIIaw9YHzZgegn52J7v7zZzz7ltozkw/98nsXwG32SHvvIVCZrt5dv47eSux9v8AsZqg7btLgAQAAAAASUVORK5CYII='
            if name.endswith(('.idx','.srt','.sub')):
                dirimage = 'data:image/gif;base64,R0lGODlhGAAYAPf/AAAbDiAfDSoqHjQlADs+J3sxJ0BALERHMk5LN1pSPUZHRk9NQU1OR05ZUFBRRFVXTVdYTVtVQFlVRFtbSF5bTVZWUltbUFlZVFtcVlxdWl5eWl1gWmBiV2FiXWNhXGRjXWlpYmtqZ2xtZmxsaG5ubHJva3Jzb3J0bHN0b3Z5dHd8eXh4dX18dXx/dnt8e31+eahMP4JdWIdnZox4cpVoYKJkXrxqablwcNA6Otg7O/8AAPwHB/0GBvgODvsMDPMbG/ceHvkSEuYqKvYqKvU2NvM6OvQ6OsFQUNVbW8N4eNd0duNeXu9aWvFUVOVqau1jY+1mZu5mZuh5eYSFgIWGgYaFgIiGgYqKiY6LioyMiY2NiYyMio2OiI6OjZCSjZSQi5OSkJGUkpSVk5WVlJWVlZiZlpiZmJ6emp2dnZSko6GhnKGhoKOjoaKnoqSkpKSmpKWmpaampqqrqKurqKqrqq2sqq6urrSyrrCwsLa3tb63tbi4t7q6ur+/vsCbm96Li9iUlMqursmwr9KwsN69veSCguiMjOiOjuaQkOWVleaXmOGfn+aYmOaamuebm+adneecnOeenuiQkOWgoOWsrOasrOWxseW2tue3t+e8vOi+vsHBwcfHx8jIxs7Mx8nJyMvLy8zMy83NzM7Pzs/Pz9PR0dTU1NXV1dXW1tbW1tfX19bb29jY2NnZ2djb29ra2tvb2tvb29za2tzc3N3d3d7e3t/f3+bCwufDw+fGxuTJyejCwujHx+nHx+vPz+rT0+rU1OrX1+vX1+rY2Ojf3+Hh4eLi4uPj4+Hn5+Tk5OXl5ebm5ufn5+nn5+jo6Onp6erp6evr6+zs7PDn5/Dq6vDt7fHv7/Lu7vPu7vPv7/Dw8PHx8fLy8vPz8/Tx8fbz8/T09PX19fX39/b29vj39/j4+Pn4+Pn5+fr5+fr6+vv7+/z7+/z8/P39/f7+/v/+/v///wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACwAAAAAGAAYAAAI/wDhCRxIsKDBgwgTZis00F27hAbRNSpSaSC7ZM6ePQsXjdmzZekKUpOio0lBVShjJXvYjp07gsEm/dLhqKC2aNG2LesES13BXJTg4dLBi2C7kPDSyQFTRY26c8akZbolkJGOaQTZFTO2LA8KCCA+zDFTp4aggVCCmCtYrJUxNiI4nAjh4o2HGW1CrhvCxGC5cOVqvcCgQQUWGRtanOkG75qOQwXbhWvZ7lOZMIGSsJjihY5AYTowFWRnipUtT6BGWIARY8IXPc1eXtIxrKC7cqJCjdJCIcIBAwRoaLqU6IkRHthGnwPzoEGKDBISMHDAZWAvHUTWjaa1J42NAgAELMBAMGCNwHbWekQxqA4VMkBKSokZE8AKtHLpjuHxo0OSQXfuLKJIOHdc0IECFaxgQivpxHGDDpYc9McS5oBTAhxUbNHFFX2I4Q4fR+iwi0GPCCGLK6rYgQYJWZDhBil7cMMJDjpAAg85L8ETCRDVqAONMuGMA0446rDjEzzi5KDDD4j48g48huxAyCqtODNZOeWcM85DAxEDzDcE+YDEK5u0EostbZ2SyizsQASPE4PAo4466TxVZzptuqmLN266GRAAOw=='
            if name.endswith('.iso'):
                dirimage = 'data:image/png;base64,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'
                # Note: a link to a directory displays with @ and links with /
            f.write(('<tr><td><img src="%s" width="24" height="24"></td><td><a href="%s">%s</a></td><td style="text-align:right; font-weight: bold; color:#FF0000">%s</td><td style="text-align:right; font-weight: bold;">%s</td></tr>\n'
                    % ( dirimage, urllib.parse.quote(linkname), html.escape(displayname) , fsize , created_date )).encode(enc))
        f.write(b"</table><hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.

        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)

        """
        # abandon query parameters
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        path = posixpath.normpath(urllib.parse.unquote(path))
        words = path.split('/')
        words = [_f for _f in words if _f]
        path = os.getcwd()
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
        return path
 
    def copyfile(self, source, outputfile):
        """Copy all data between two file objects.

        The SOURCE argument is a file object open for reading
        (or anything with a read() method) and the DESTINATION
        argument is a file object open for writing (or
        anything with a write() method).

        The only reason for overriding this would be to change
        the block size or perhaps to replace newlines by CRLF
        -- note however that this the default server uses this
        to copy binary data as well.

        """
        shutil.copyfileobj(source, outputfile)
 
    def guess_type(self, path):
        """Guess the type of a file.

        Argument is a PATH (a filename).

        Return value is a string of the form type/subtype,
        usable for a MIME Content-type header.

        The default implementation looks the file's extension
        up in the table self.extensions_map, using application/octet-stream
        as a default; however it would be permissible (if
        slow) to look inside the data to make a better guess.

        """
 
        base, ext = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']
 
    if not mimetypes.inited:
        mimetypes.init() # try to read system mime.types
    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'application/octet-stream', # Default
        '.py': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
        })
 
parser = argparse.ArgumentParser()
parser.add_argument('--bind', '-b', default='', metavar='ADDRESS',
                        help='Specify alternate bind address '
                             '[default: all interfaces]')
parser.add_argument('port', action='store',
                        default=8000, type=int,
                        nargs='?',
                        help='Specify alternate port [default: 8000]')
args = parser.parse_args()

PORT = args.port
BIND = args.bind
HOST = BIND

if HOST == '':
	HOST = 'localhost'

Handler = SimpleHTTPRequestHandler

with socketserver.TCPServer((BIND, PORT), Handler) as httpd:
	serve_message = "Serving HTTP on {host} port {port} (http://{host}:{port}/) ..."
	print(serve_message.format(host=HOST, port=PORT))
	httpd.serve_forever()


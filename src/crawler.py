import os
import sys
import Queue
import urllib
import httplib
import urllib2
import Queue
import threading

from optparse import OptionParser, SUPPRESS_HELP
from BeautifulSoup import BeautifulSoup, SoupStrainer


validContentTypes = ("text/html", "application/xhtml+xml")

class Crawler:
    # Gets      : Starting URL, maxsize of repo and number of retries for data fetch
    # Returns   : None
    def __init__(self, url, maxcount, retries = 1):
        self.repo       = []
        self.maxcount   = maxcount
        self.retries    = retries
        self.currptr    = 0
        self.abort      = False
        self.lock       = threading.Lock()

        self.__push(url)

    def __cleanurl(self, url):
        return url.strip("/")

    # Gets      : Url to be put into the repo
    # Returns   : None
    # This function sets the abort flag if there is nothing more is to be done
    def __push(self, url):
        url = self.__cleanurl(url) # Bring all urls to same sandard to detect duplicate
        with self.lock:
            if not url in self.repo:
                self.repo.append(url)

        if self.maxcount <> -1 and len(self.repo) == self.maxcount:
            self.abort = True

        return

    @property
    def totalurls(self):
        return len(self.repo)

    # Gets      : Nothing
    # Returns   : Url at currptr or None
    # This function sets the abort flag if all entries in repo are processed
    def __pop(self):
        url = None
        if self.currptr == len(self.repo):
            self.abort = True
        else:
            with self.lock:
                url = self.repo[self.currptr]
                self.currptr += 1
        return url

    # Given a url it returns the stripped down url
    # eg http//:www.google.com/doc/ will return http//www.google.com
    def __get_orig_url(self, url):
        if url.startswith("http://"):
            return "http://" + url[7:].split("/")[0]
        elif url.startswith("https://"):
            return "https://" + url[8:].split("/")[0]
            
        return url
        
    # Check if its a valid url to be crawled for or not
    def __valid_contenttype(self, ctype):
        valid = False
        for validctype in validContentTypes:
            if ctype.find(validctype) > -1:
                valid = True
                break
        return valid

    # Given a url and number of retries getHtmlData will return the html data
    def getHtmlData(self, url):
        cur_try     = 0
        nothing     = (None, None)
        
        #just basic urls
        if not url.startswith('http://'):
            return nothing
        while True:
            try:
                req = urllib2.Request(url)
                open_req = urllib2.urlopen(req)

                content_type = open_req.headers.get('content-type')
                if not self.__valid_contenttype(content_type):
                    print "Discarding %s for content %s"%(url, content_type)
                    return nothing

                content = open_req.read()
                return (content_type, content)

            except (urllib2.URLError, urllib2.HTTPError, httplib.InvalidURL), e:
                cur_try += 1
                if cur_try >= self.retries:
                    print('error while fetching: %s ' % (url))
                    print(e)
                    return
            finally:
                if 'open_req' in locals():
                    open_req.close()

    # Gets: baseurl (The url from where we reach here), current url
    # returns: absolute url. 
    #
    # Convert tags to url. This follows three rules
    # If given url starts with "/" then add this to the orignal url of baseurl
    # If given url starts with "http" or httpsthen no change required
    # Else just add this to the baseurl and return
    def get_absurl(self, baseurl, currurl):
        final_url = currurl
        
        if currurl.startswith("http://") or currurl.startswith("https://"):
            pass
        elif currurl.startswith("/"):
            final_url =  self.__get_orig_url(baseurl) + currurl
        elif currurl.startswith("#"):
            final_url =  self.__get_orig_url(baseurl) + '/' + currurl
        else:
            final_url = baseurl + currurl

        return final_url

    # Extract links from th HTML data. 
    # Also take care not to put links in repo if repo is full
    def extractLinks(self, baseurl, html):
        links = BeautifulSoup(html) 
        for link in links.findAll('a'):
            if self.abort:
                return
            if link.get("href"):
                self.__push(self.get_absurl(baseurl, link["href"]))
        return

    # Does the crawling and stops if gets a abort flag
    def doCrawling(self):
        while not self.abort:
            currurl = self.__pop()
            if currurl == None:
                continue
            cont_type, htmlData = self.getHtmlData(currurl)
            if htmlData:
                self.extractLinks(currurl, htmlData)

# Pass url with -u option.
# Pass max number of links to be collected with -c option
if __name__ == '__main__':
    parser = OptionParser(usage=__doc__, version="LinkCrawler 1.0")
    parser.add_option("-u", "--url", action="store", dest="url",
                          help="url to be crawled",
                          type='string', default='')
    parser.add_option("-c", "--count", action="store", dest="maxcount",
                          help="Maximum number of links to be collected",
                          type='int', default=-1)
    options, args = parser.parse_args(sys.argv)

    if options.url == "":
        sys.stdout.write("Please provide the starting url [http://python.org]: ")
        options.url = raw_input()
        if not options.url:
            options.url = "http://python.org"

    if not options.url.startswith("http://"):
        options.url = "http://" + options.url

    crawlobj = Crawler(options.url, options.maxcount)
    crawlobj.doCrawling()
    print "Collected %d Links"%crawlobj.totalurls
    showrepo = raw_input("Do you want to see the repository y/n [y]: ")
    if showrepo == '' or showrepo == 'y' or showrepo == 'Y' or showrepo == 'yes':
        count = 1
        for elem in crawlobj.repo:
            print "%d.\t%s"%(count, elem)
            count += 1
    

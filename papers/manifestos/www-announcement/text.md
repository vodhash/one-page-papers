```
From: timbl@info .cern.ch (Tim Berners-Lee)
Newsgroups: alt.hypertext
Subject: Re: Qualifiers on Hypertext links...
Message-ID: <6484@cernvax.cern.ch>
Date: 6 Aug 91 14:56:20 GMT
References: <1991Aug2.115241@ardor.enet.dec.com>
Sender: news@cernvax.cern.ch
Lines: 52


In article <1991Aug2.115241@ardor.enet.dec.com> kannan@ardor.enet.dec.com (Nari  
Kannan) writes:
> 
>    Is anyone reading this newsgroup aware of research or development efforts  
 in
> the
>    following areas:
> 
>     1. Hypertext links enabling retrieval from multiple heterogeneous sources  
 of
> information?

The WorldWideWeb (WWW) project aims to allow links to be made to any  
information anywhere. The address format includes an access method  
(=namespace), and for most name spaces a hostname and some sort of path.

We have a prototype hypertext editor for the NeXT, and a browser for line mode  
terminals which runs on almost anything. These can access files either locally,  
NFS mounted, or via anonymous FTP. They can also go out using a simple protocol  
(HTTP) to a server which interprets some other data and returns equivalent  
hypertext files. For example, we have a server running on our mainframe  
(http://cernvm.cern.ch/FIND in WWW syntax) which makes all the CERN computer  
center documentation available. The HTTP protocol allows for a keyword search  
on an index, which generates a list of matching documents as annother virtual  
hypertext document.

If you're interested in using the code, mail me.  It's very prototype, but  
available by anonymous FTP from info.cern.ch. It's copyright CERN but free  
distribution and use is not normally a problem.

The NeXTstep editor can also browse news. If you are using it to read this,  
then click on this: <http://info.cern.ch/hypertext/WWW/TheProject.html> to find  
out more about the project. We haven't put the news access into the line mode  
browser yet.

We also have code for a hypertext server. You can use this to make files  
available (like anonymous FTP but faster because it only uses one connection).  
You can also hack it to take a hypertext address and generate a virtual  
hypertext document from any other data you have - database, live data etc. It's  
just a question of generating plain text or SGML (ugh! but standard) mark-up on  
the fly. The browsers then parse it on the fly. 

The WWW project was started to allow high energy physicists to share data,  
news, and documentation. We are very interested in spreading the web to other  
areas, and having gateway servers for other data.  Collaborators welcome! I'll  
post a short summary as a separate article.


Tim Berners-Lee				timbl@info.cern.ch
World Wide Web project			Tel: +41(22)767 3755	
CERN					Fax: +41(22)767 7155
1211 Geneva 23, Switzerland 		(usual disclaimer)
```

```
From: timbl@info .cern.ch (Tim Berners-Lee)
Newsgroups: alt.hypertext
Subject: WorldWideWeb: Summary
Keywords: heterogeneous hypertext, web, source, protocol, index, information retrieval
Message-ID: <6487@cernvax.cern.ch>
Date: 6 Aug 91 16:00:12 GMT
References: <6484@cernvax.cern.ch>
Sender: news@cernvax.cern.ch
Lines: 84


In article <6484@cernvax.cern.ch> I promised to post a short summary  of the  
WorldWideWeb project.  Mail me with any queries.

		WorldWideWeb - Executive Summary


The WWW project merges the techniques of information retrieval and hypertext to  
make an easy but powerful global information system.

The project started with the philosophy that much academic information should  
be freely available to anyone. It aims to allow information sharing within  
internationally dispersed teams, and the dissemination of information by  
support groups.

     Reader view

The WWW world consists of documents, and links.  Indexes are special documents  
which, rather than being read, may be searched. The result of such a search is  
another ("virtual") document containing links to the documents found.  A simple  
protocol ("HTTP") is used to allow a browser program to request a keyword  
search by a remote information server. 

The web contains documents in many formats. Those documents which are  
hypertext,  (real or virtual) contain links to other documents, or places  
within documents. All documents, whether real, virtual or indexes, look similar  
to the reader and are contained within the same addressing scheme.

To follow a link,  a reader clicks with a mouse (or types in a number if he or  
she has no mouse). To search and index, a reader gives keywords (or other  
search criteria). These are the only operations  necessary to access the entire  
world of data.

     Information provider view

The WWW browsers can access many existing data systems via existing protocols  
(FTP, NNTP) or via HTTP and a gateway. In this way, the critical mass of data  
is quickly exceeded, and the increasing use of the system by readers and  
information suppliers encourage each other.

Making a web is as simple as writing a few SGML files which point to your  
existing data. Making it public involves running the FTP or HTTP daemon, and  
making at least one link into your web from another. In fact,  any file  
available by anonymous FTP can be immediately linked into a web. The very small  
start-up effort is designed to allow small contributions.  At the other end of  
the scale, large information providers may provide an HTTP server with full  
text or keyword indexing.

The WWW model gets over the frustrating incompatibilities of data format  
between suppliers and reader by allowing negotiation of format between a smart  
browser and a smart server. This should provide a basis for extension into  
multimedia, and allow those who share application standards to make full use of  
them across the web.

This summary does not describe the many exciting possibilities opened up by the  
WWW project, such as efficient document caching. the reduction of redundant  
out-of-date copies, and the use of knowledge daemons.  There is more  
information in the online project documentation, including some background on  
hypertext and many technical notes. 

     Try it

A prototype (very alpha test) simple line mode browser is currently available  
in source form from node  info.cern.ch [currently 128.141.201.74] as

	/pub/WWW/WWWLineMode_0.9.tar.Z.

Also available is a hypertext editor for the NeXT using the NeXTStep graphical  
user interface, and a skeleton server daemon.

Documentation is readable using www (Plain text of the instalation instructions  
is included in the tar file!). Document

         http://info.cern.ch/hypertext/WWW/TheProject.html

is as good a place to start as any. Note these coordinates may change with  
later releases.

_________________________________________________________________

Tim Berners-Lee			Tel:	+41(22)767 3755
WorldWideWeb project		Fax:	+41(22)767 7155
C.E.R.N.			email:	tbl@cernvax.cern.ch
1211 Geneva 23
Switzerland
```

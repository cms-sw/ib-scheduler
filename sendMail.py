

def sendMail(sender, to, subject, msgIn):

    # Import smtplib for the actual sending function
    import smtplib

    for toAddr in to:
        msg = ("From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n" % (sender, toAddr, subject) )

        msg += msgIn
    
        # Send the message via our own SMTP server, but don't include the
        # envelope header.
        s = smtplib.SMTP()
        s.connect()
        s.sendmail(sender, toAddr, msg)
        s.close()

    return


if __name__ == '__main__':

    msg = "Hi, ... \n\n"
    
    addrFrom = "cmsbuild@cern.ch"
    addrTo   = ["voviss@gmail.com", 'vskarupe@cern.ch']
    subj     = 'results from customIB'
    sendMail(addrFrom, addrTo, subj, msg)


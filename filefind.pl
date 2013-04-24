#!/usr/bin/perl 
#____________________________________________________________________ 
# File: FileFindTest.pl
#____________________________________________________________________ 
#  
# Author: Shaun Ashby <Shaun.Ashby@cern.ch>
# Update: 2003-10-28 12:48:44+0100
# Revision: $Id$ 
# 
# Copyright: 2003 (C) Shaun Ashby
#
#--------------------------------------------------------------------
use File::Find;
use Cwd;

use vars qw/*name *dir *prune/;
*name   = *File::Find::name;
*dir    = *File::Find::dir;
*prune  = *File::Find::prune;

my %administrators=();

# Force flush:
$|=1;
my $wd=cwd();

# Read the list of files found under directory:
File::Find::find({wanted => \&collect}, "src");

#### Subroutines ####
sub collect
   {
   if (my ($packagename) = ($name =~ m|^src/(.*?)/.admin/developers|))
      {
      open(DEVELOPERS, "$wd/$name") || die "$name: $!","\n";
      while(<DEVELOPERS>)
	 {
	 chomp;
	 if ($_ =~ m|.*:.(.*?)@(.*)|)
	    {	    
	    if (exists $administrators{$packagename})
	       {
	       $administrators{$packagename}="$administrators{$packagename}".",$1\@$2";
     
} else 
{
     $administrators{$packagename} = "$1\@$2";
}
	    }
	 }
      close(DEVELOPERS);
      
      }

   }

foreach $keys (keys %administrators) {
    print "$keys -> $administrators{$keys}\n";
}

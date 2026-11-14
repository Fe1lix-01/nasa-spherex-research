#! /bin/sh
cat <<EOF
************************************************
*
*    Date: Fri Nov 13 20:43:52 PST 2026
*
*    Script to download SPHEREx data from IRSA
*
*    The script below defines a subroutine to download the files
*
************************************************

EOF
    download_file() {

      href="$1"
      targetDir="$2"
      baseFileName="$3"
      suffix="$4"

      startDir=$(pwd)

      # create temp dir
      tmpDir=$(mktemp -d)
      cd "$tmpDir" || return 1

      echo ">> downloading ${href} ..."
      cmd="curl -fLJO"
      $cmd "$href" || {
        echo ">> ERROR: failed to download ${href}"
        cd "$startDir"
        rm -rf "$tmpDir"
        return 1
      }

      # get most recently modified file
      downloadedFile=$(ls -t | head -n 1)

      # determine filename
      if [ -n "$baseFileName" ]; then
        ext="${baseFileName##*.}"
        name="${baseFileName%.*}"
      else
        ext="${downloadedFile##*.}"
        name="${downloadedFile%.*}"
      fi

      # Apply suffix, if available
      finalName="$name"
      [ -n "$suffix" ] && finalName="${finalName}-$suffix"
      finalFile="${finalName}.${ext}"

      # create target dir in current directory
      if [ -n "$targetDir" ]; then
        destDir="$startDir/$targetDir"
      else
        destDir="$startDir"
      fi
      mkdir -p "$destDir"

      # resolve naming conflicts
      destPath="$destDir/$finalFile"
      count=1
      while [ -e "$destPath" ]; do
        destPath="$destDir/${finalName} (${count}).${ext}"
        count=$((count + 1))
      done

      # move file to main directory and cleanup
      mv "$downloadedFile" "$destPath"
      echo ">> Saved as $destPath"

      

      cd "$startDir"
      rm -rf "$tmpDir"
    }

download_file 'https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/level2/2025W38_1A/l2b-v27-2026-237/6/level2_2025W38_1A_0596_1D6_spx_l2b-v27-2026-237.fits' 'SPHERExLVFSurveyData' '' ''
download_file 'https://irsa.ipac.caltech.edu/ibe/cutout?ra=294.43003651&dec=-13.62324433&size=0.02&path=spherex/dr1/level2/2025W38_1A/l2b-v27-2026-237/6/level2_2025W38_1A_0596_1D6_spx_l2b-v27-2026-237.fits' 'SPHERExLVFSurveyData' '' 'cutout'
download_file 'https://irsa.ipac.caltech.edu/ibe/data/spherex/qr3/level2/2026W39_2A/l2b-v27-2026-271/6/level2_2026W39_2A_0324_4D6_spx_l2b-v27-2026-271.fits' 'SPHERExLVFSurveyData-1' '' ''
download_file 'https://irsa.ipac.caltech.edu/ibe/cutout?ra=295.13749638&dec=-16.59234218&size=0.02&path=spherex/qr3/level2/2026W39_2A/l2b-v27-2026-271/6/level2_2026W39_2A_0324_4D6_spx_l2b-v27-2026-271.fits' 'SPHERExLVFSurveyData-1' '' 'cutout'

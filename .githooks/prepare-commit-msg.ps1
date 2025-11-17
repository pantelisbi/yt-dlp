# PowerShell prepare-commit-msg hook
# Automatically add "Authored by: <github-username>" to commit messages

$commitMsgFile = $args[0]
$commitSource = $args[1]

# Only add for regular commits (not merge, squash, etc.)
if ([string]::IsNullOrEmpty($commitSource) -or $commitSource -eq "message") {
    $content = Get-Content $commitMsgFile -Raw -ErrorAction SilentlyContinue
    
    if ($content -and $content -notmatch "(?m)^Authored by:") {
        # Get GitHub username from git config
        $githubUser = git config user.github
        
        # If not set, try to extract from remote URL
        if ([string]::IsNullOrEmpty($githubUser)) {
            $remoteUrl = git config remote.origin.url
            if ($remoteUrl -match 'github\.com[:/]([^/]+)/') {
                $githubUser = $Matches[1]
            }
        }
        
        # Add a blank line if the message doesn't end with one
        if ($content -notmatch "\n\s*$") {
            $content += "`n"
        }
        $content += "`nAuthored by: $githubUser"
        
        Set-Content -Path $commitMsgFile -Value $content -NoNewline
    }
}

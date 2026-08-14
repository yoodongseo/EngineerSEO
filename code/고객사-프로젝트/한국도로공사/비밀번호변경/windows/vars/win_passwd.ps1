param(
    [string]$username,
    [string]$newPassword
)

try {
    # 사용자 계정의 패스워드 변경
    Set-LocalUser -Name $username -Password (ConvertTo-SecureString -AsPlainText $newPassword -Force)

    $message = "패스워드 변경이 완료되었습니다."
    Write-Output $message
} catch {
    $errorMessage = "패스워드 변경이 실패했습니다. 에러: $_"
    Write-Output $errorMessage
    exit 1
}

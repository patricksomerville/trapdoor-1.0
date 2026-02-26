class Trapdoor < Formula
  desc "Give cloud AIs safe access to your local machine (with access tiers)"
  homepage "https://github.com/patricksomerville/trapdoor-1.0"
  url "https://github.com/patricksomerville/trapdoor-1.0/archive/refs/tags/v0.1.1.tar.gz"
  sha256 "23e78aa286b12067ad979d9732df56c57fe0c423bd75813a59f79bc4506c243f"
  license "MIT"

  depends_on "python@3.12"

  def install
    venv = virtualenv_create(libexec, "python3")
    venv.pip_install buildpath
    (bin/"trapdoor").write_env_script(libexec/"bin/trapdoor", {})
  end

  test do
    assert_match "Trapdoor", shell_output("#{bin}/trapdoor --help")
  end
end
